"""Synchronous, read-only live GPT-to-Codex pipeline."""
from __future__ import annotations

import copy
import csv
import dataclasses
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from app import config
from app.codex.client import CodexProposalRequest
from app.codex.live_client import CodexExecutionError
from app.llm.validate import validate_output
from app.pipeline.live_checks import execute_live_checks
from app.store.db import Store
from app.store.models import ArtifactRow, FailureRow, PatchRow, RequirementRow, TestRow
from app.store.state_machine import transition_run


class LiveInputError(ValueError): pass

class LivePipelineError(RuntimeError):
    def __init__(self, run_id: str, stage: str, message: str = "live pipeline failed"):
        super().__init__(message); self.run_id = run_id; self.stage = stage


@dataclass(frozen=True)
class LiveRunInputs:
    implementation_doc_path: Path
    source_data_path: Path
    target_schema_path: Path


def _validate_path(path: Path, suffix: str) -> Path:
    raw = str(path)
    if path.is_absolute() or "\\" in raw or ".." in path.parts:
        raise LiveInputError("input paths must be safe repository-relative fixture paths")
    candidate = config.REPO_ROOT / path
    if candidate.is_symlink() or not candidate.is_file() or candidate.suffix != suffix:
        raise LiveInputError("input path is not a permitted regular file")
    try: candidate.resolve().relative_to(config.FIXTURES_DIR.resolve())
    except ValueError as error: raise LiveInputError("input must be inside fixtures") from error
    return candidate


def validate_inputs(inputs: LiveRunInputs) -> tuple[Path, Path, Path, str, dict[str, Any]]:
    doc, source, schema_path = (_validate_path(inputs.implementation_doc_path, ".md"),
                                _validate_path(inputs.source_data_path, ".csv"),
                                _validate_path(inputs.target_schema_path, ".json"))
    try:
        implementation = doc.read_text(encoding="utf-8")
        with source.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle); rows = list(reader); header = reader.fieldnames
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error: raise LiveInputError("inputs must be valid UTF-8 data") from error
    expected = ["record_id", "account_id", "branch", "effective_date", "amount", "txn_code"]
    ids = [r.get("record_id", "") for r in rows]
    if not implementation.strip() or header != expected or any(not x for x in ids) or len(ids) != len(set(ids)):
        raise LiveInputError("implementation document or CSV is invalid")
    try: Draft202012Validator.check_schema(schema)
    except Exception as error: raise LiveInputError("target schema is not valid JSON Schema") from error
    if schema.get("type") != "object" or set(schema.get("required", [])) != set(expected[1:]):
        raise LiveInputError("target schema has invalid required fields")
    return doc, source, schema_path, implementation, schema


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, default=lambda x: format(x, ".2f") if isinstance(x, Decimal) else str(x)) + "\n", encoding="utf-8")


def _artifact(store: Store, run_id: str, path: Path, kind: str, producer: str, client: str,
              validation: str, created_at: str) -> str:
    aid = store.allocate_id("ART", start=10)
    store.insert_artifact(ArtifactRow(aid, run_id, kind, path.relative_to(config.REPO_ROOT).as_posix(),
        hashlib.sha256(path.read_bytes()).hexdigest(), producer, "live", client, validation, created_at))
    return aid


def run_live_pipeline(store: Store, inputs: LiveRunInputs, llm_client: Any, codex_client: Any):
    doc, source, schema_path, implementation, schema = validate_inputs(inputs)
    store.init_schema(); run_id = store.allocate_id("RUN", start=2)
    run = store.create_run("live", config.SCHEMA_VERSION, run_id=run_id); stage = "ingest"
    registered: set[str] = set()
    try:
        doc_a = _artifact(store, run_id, doc, "input", "deterministic", "none", "not_required", run.created_at)
        source_a = _artifact(store, run_id, source, "input", "deterministic", "none", "not_required", run.created_at)
        schema_a = _artifact(store, run_id, schema_path, "input", "deterministic", "none", "not_required", run.created_at)
        transition_run(store, run_id, "INGESTED", "live_pipeline"); stage = "manifest"
        manifest = llm_client.extract_requirements(implementation_doc=implementation, run_id=run_id,
                                                    source_artifact_ids=[doc_a])
        raw_llm = config.QUARANTINE_DIR / "llm" / run_id / "control_manifest.raw.json"
        if raw_llm.is_file(): _artifact(store, run_id, raw_llm, "raw_model_output", "gpt-5.6", "LiveLLMClient", "quarantined", run.created_at); registered.add(str(raw_llm))
        required = [("field_validation", "preserve account identifiers verbatim"),
                    ("balancing_rule", "debits equal credits by branch"),
                    ("exception_handling", "no silent value substitution")]
        actual = [(r.get("rule_type"), r.get("text", "").strip().lower().removesuffix(".")) for r in manifest.get("requirements", [])]
        if actual != required: raise ValueError(f"manifest requirements did not match required controls: expected {required}, got {actual}")
        normalized = copy.deepcopy(manifest); req_ids = store.allocate_ids("REQ", 3, start=4)
        for item, rid in zip(normalized["requirements"], req_ids): item["requirement_id"] = rid
        validate_output("control_manifest.schema.json", normalized)
        run_dir = config.LIVE_RUNS_DIR / run_id; manifest_path = run_dir / "control_manifest.validated.json"; _json(manifest_path, normalized)
        manifest_a = _artifact(store, run_id, manifest_path, "validated_model_output", "gpt-5.6", "LiveLLMClient", "validated", run.created_at)
        for item in normalized["requirements"]: store.insert_requirement(RequirementRow(item["requirement_id"], run_id, item["text"], item["rule_type"], item.get("tolerance"), item["provenance"]))
        transition_run(store, run_id, "MANIFEST_READY", "live_pipeline"); stage = "tests"
        test_ids = store.allocate_ids("TEST", 3, start=4); names = ("preserve_account_identifiers_verbatim", "balance_debits_and_credits_by_branch", "reject_unparseable_effective_dates")
        provenance = {"schema_version": config.SCHEMA_VERSION, "run_id": run_id, "created_at": run.created_at,
          "source_artifact_ids": [manifest_a, source_a, schema_a], "producer": "deterministic", "mode": "live", "client": "none", "validation_status": "not_required"}
        for tid, rid, name in zip(test_ids, req_ids, names): store.insert_test(TestRow(tid, run_id, rid, name, "pending", None, provenance))
        transition_run(store, run_id, "TESTS_GENERATED", "live_pipeline"); stage = "execute"
        checked = execute_live_checks(source, schema); failure_ids = store.allocate_ids("FAIL", 3, start=4)
        failure_payloads = []
        for detected, fid, rid, tid in zip(checked["failures"], failure_ids, req_ids, test_ids):
            payload = {**detected, "failure_id": fid, "requirement_id": rid, "provenance": provenance}; validate_output("failed_record.schema.json", payload); failure_payloads.append(payload)
            store.insert_failure(FailureRow(fid, run_id, rid, tid, detected["record_id"], detected["field"], detected["expected"], detected["actual"], "blocking", detected["record_hash"], provenance))
        result = checked["result"]
        output = {"run_id": run_id, "mode": "live", "source_data_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "target_schema_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
          "migrated_records": result.migrated_records, "rejected_records": result.rejected_records, "branch_balances": [vars(x) for x in result.branch_balances],
          "checks": sorted([{"requirement_id": r, "test_id": t, "rule_type": normalized["requirements"][i]["rule_type"], "status": "failed", "failure_ids": [failure_ids[i]]} for i,(r,t) in enumerate(zip(req_ids,test_ids))], key=lambda x:x["test_id"])}
        output_path = run_dir / "migration_test_output.json"; _json(output_path, output); output_a = _artifact(store, run_id, output_path, "test_output", "deterministic", "none", "not_required", run.created_at)
        for tid in test_ids: store.set_test_result(tid, "failed", output_a)
        transition_run(store, run_id, "EXECUTED", "live_pipeline"); transition_run(store, run_id, "TRIAGED", "live_pipeline"); stage = "codex"
        patch_id = store.allocate_id("PATCH", start=2)
        context = {"implementation_doc": implementation, "control_manifest": normalized, "failures": failure_payloads, "migration_test_output_path": output_path.relative_to(config.REPO_ROOT).as_posix(), "goal": "Repair all detected migration defects while modifying only reconcile/migration.py", "required_outcomes": ["preserve account identifiers verbatim", "reject unparseable effective dates through the existing rejection path", "treat CREDIT_ADJUSTMENT as a credit", "make Branch 101 balance at 1250.00 debit, 1250.00 credit, 0.00 difference"], "forbidden_changes": ["contracts", "fixtures", "tests", "frontend", "dependencies", "any file except reconcile/migration.py"]}
        request = CodexProposalRequest(config.REPO_ROOT, run_id, patch_id, failure_ids, ("reconcile/migration.py",), (manifest_a, output_a), config.SCHEMA_VERSION, run.created_at, json.dumps(context, sort_keys=True), 1)
        # Codex output varies; a proposal that fails validation (including the
        # real apply check) gets exactly one retry, with the failed attempt
        # left quarantined for the audit trail.
        try:
            proposal = codex_client.propose_patch(request)
        except CodexExecutionError:
            request = dataclasses.replace(request, attempt=2)
            proposal = codex_client.propose_patch(request)
        quarantine = config.QUARANTINE_DIR / "codex" / run_id / patch_id / f"{request.attempt:03d}"
        for filename, kind in (("proposal.raw.json", "raw_model_output"), ("events.jsonl", "log"), ("stderr.log", "log")):
            path = quarantine / filename
            if path.is_file(): _artifact(store, run_id, path, kind, "codex", "LiveCodexClient", "quarantined", run.created_at); registered.add(str(path))
        proposal_path = run_dir / f"{patch_id}.validated.json"; _json(proposal_path, proposal); proposal_a = _artifact(store, run_id, proposal_path, "patch_diff", "codex", "LiveCodexClient", "validated", run.created_at)
        store.insert_patch(PatchRow(patch_id, run_id, list(failure_ids), proposal["diff"], "pending", None, None, None, proposal["provenance"]))
        transition_run(store, run_id, "PATCH_PENDING", "live_pipeline"); return store.get_run(run_id)
    except Exception as error:
        for path in config.QUARANTINE_DIR.glob(f"**/{run_id}/**/*"):
            if path.is_file() and str(path) not in registered:
                try: _artifact(store, run_id, path, "log" if path.name != "proposal.raw.json" and path.name != "control_manifest.raw.json" else "raw_model_output", "codex" if "codex" in path.parts else "gpt-5.6", "LiveCodexClient" if "codex" in path.parts else "LiveLLMClient", "quarantined", run.created_at)
                except Exception: pass
        current = store.get_run(run_id)
        if current and current.state != "FAILED": transition_run(store, run_id, "FAILED", "live_pipeline")
        raise LivePipelineError(run_id, stage) from error
