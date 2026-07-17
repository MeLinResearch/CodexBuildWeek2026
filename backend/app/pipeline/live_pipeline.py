from __future__ import annotations

import csv
import hashlib
import io
import json
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from jsonschema import Draft202012Validator, SchemaError

from app import config
from app.codex.client import CodexProposalRequest
from app.llm.validate import validate_output
from app.pipeline.live_checks import format_decimal, run_live_checks
from app.store.db import Store
from app.store.models import ArtifactRow, FailureRow, PatchRow, RequirementRow, RunRow, TestRow
from app.store.state_machine import transition_run

CSV_HEADER = ("record_id", "account_id", "branch", "effective_date", "amount", "txn_code")
TARGET_SCHEMA_REQUIRED_FIELDS = frozenset({"account_id", "branch", "effective_date", "amount", "txn_code"})

EXPECTED_REQUIREMENTS = (
    ("field_validation", "preserve account identifiers verbatim"),
    ("balancing_rule", "debits equal credits by branch"),
    ("exception_handling", "no silent value substitution"),
)
LIVE_TEST_NAMES = (
    "preserve_account_identifiers_verbatim",
    "balance_debits_and_credits_by_branch",
    "reject_unparseable_effective_dates",
)
REQUIRED_OUTCOMES = (
    "preserve account identifiers verbatim",
    "reject unparseable effective dates through the existing rejection path",
    "treat CREDIT_ADJUSTMENT as a credit",
    "make Branch 101 balance at 1250.00 debit, 1250.00 credit, 0.00 difference",
)
FORBIDDEN_CHANGES = (
    "contracts",
    "fixtures",
    "tests",
    "frontend",
    "dependencies",
    "any file except reconcile/migration.py",
)
CODEX_GOAL = "Repair all detected migration defects while modifying only reconcile/migration.py"


class LiveInputError(ValueError):
    """Raised when the three live run input files fail validation."""


class LivePipelineError(RuntimeError):
    def __init__(self, run_id: str, stage: str, message: str) -> None:
        super().__init__(message)
        self.run_id = run_id
        self.stage = stage
        self.message = message


class _LiveManifestMismatch(RuntimeError):
    """Raised internally when the model's requirements do not match the expected manifest."""


@dataclass(frozen=True)
class LiveRunInputs:
    implementation_doc_path: Path
    source_data_path: Path
    target_schema_path: Path


@dataclass(frozen=True)
class ValidatedLiveInputs:
    implementation_doc_path: Path
    implementation_doc_text: str
    source_data_path: Path
    source_records: tuple[dict[str, str], ...]
    target_schema_path: Path
    target_schema: dict[str, Any]


def _read_utf8(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise LiveInputError(f"could not read {path.name}") from error
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LiveInputError(f"{path.name} must be UTF-8 encoded") from error


def _resolve_fixture_path(raw_path: Path, expected_suffix: str) -> Path:
    raw = str(raw_path)
    if not raw:
        raise LiveInputError("path is required")
    if "\\" in raw:
        raise LiveInputError("path must not contain backslashes")
    if raw_path.is_absolute():
        raise LiveInputError("path must be repository-relative")
    if any(part in ("..", ".") for part in raw_path.parts):
        raise LiveInputError("path must not traverse directories")
    if raw_path.suffix != expected_suffix:
        raise LiveInputError(f"path must end with {expected_suffix}")
    candidate = config.REPO_ROOT / raw_path
    if not candidate.exists():
        raise LiveInputError("path does not exist")
    if candidate.is_symlink():
        raise LiveInputError("path must not be a symlink")
    if not candidate.is_file():
        raise LiveInputError("path must be a regular file")
    resolved = candidate.resolve(strict=True)
    if resolved != candidate:
        raise LiveInputError("path must not traverse a symlink")
    fixtures_root = config.FIXTURES_DIR.resolve()
    if resolved != fixtures_root and fixtures_root not in resolved.parents:
        raise LiveInputError("path must be inside the fixtures directory")
    return candidate


def validate_live_run_inputs(inputs: LiveRunInputs) -> ValidatedLiveInputs:
    if inputs.implementation_doc_path is None or inputs.source_data_path is None or inputs.target_schema_path is None:
        raise LiveInputError("implementation_doc_path, source_data_path, and target_schema_path are all required")

    doc_path = _resolve_fixture_path(inputs.implementation_doc_path, ".md")
    csv_path = _resolve_fixture_path(inputs.source_data_path, ".csv")
    schema_path = _resolve_fixture_path(inputs.target_schema_path, ".json")

    doc_text = _read_utf8(doc_path)
    if not doc_text.strip():
        raise LiveInputError("implementation document must not be empty")

    csv_text = _read_utf8(csv_path)
    header_rows = list(csv.reader(io.StringIO(csv_text)))
    if not header_rows or tuple(header_rows[0]) != CSV_HEADER:
        raise LiveInputError("source data CSV header is invalid")
    records = list(csv.DictReader(io.StringIO(csv_text)))
    seen_record_ids: set[str] = set()
    for record in records:
        record_id = record.get("record_id") or ""
        if not record_id:
            raise LiveInputError("source data record_id must be nonempty")
        if record_id in seen_record_ids:
            raise LiveInputError("source data record_id values must be unique")
        seen_record_ids.add(record_id)

    schema_text = _read_utf8(schema_path)
    try:
        schema = json.loads(schema_text)
    except json.JSONDecodeError as error:
        raise LiveInputError("target schema must be valid JSON") from error
    if not isinstance(schema, dict):
        raise LiveInputError("target schema must be a JSON object")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise LiveInputError("target schema must be a valid JSON Schema") from error
    if schema.get("type") != "object":
        raise LiveInputError("target schema type must be object")
    required = schema.get("required")
    if not isinstance(required, list) or set(required) != TARGET_SCHEMA_REQUIRED_FIELDS:
        raise LiveInputError("target schema required fields do not match the contract")

    return ValidatedLiveInputs(
        implementation_doc_path=doc_path,
        implementation_doc_text=doc_text,
        source_data_path=csv_path,
        source_records=tuple(records),
        target_schema_path=schema_path,
        target_schema=schema,
    )


def _repo_relative_posix(path: Path) -> str:
    return path.resolve().relative_to(config.REPO_ROOT.resolve()).as_posix()


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _persist_artifact(
    store: Store,
    *,
    artifact_id: str,
    run_id: str,
    kind: str,
    path: Path,
    producer: str,
    mode: str,
    client: str,
    validation_status: str,
    created_at: str,
) -> ArtifactRow:
    row = ArtifactRow(
        artifact_id=artifact_id,
        run_id=run_id,
        kind=kind,
        path=_repo_relative_posix(path),
        sha256=_sha256_path(path),
        producer=producer,
        mode=mode,
        client=client,
        validation_status=validation_status,
        created_at=created_at,
    )
    return store.insert_artifact(row)


def _provenance(
    run_id: str,
    created_at: str,
    source_artifact_ids: Sequence[str],
    producer: str,
    mode: str,
    client: str,
    validation_status: str,
) -> dict[str, Any]:
    return {
        "schema_version": config.SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": created_at,
        "source_artifact_ids": list(source_artifact_ids),
        "producer": producer,
        "mode": mode,
        "client": client,
        "validation_status": validation_status,
    }


def _normalize_requirement_text(text: str) -> str:
    normalized = text.strip().lower()
    if normalized.endswith("."):
        normalized = normalized[:-1]
    return normalized


def _validate_manifest_requirements(requirements: list[dict[str, Any]]) -> None:
    if len(requirements) != len(EXPECTED_REQUIREMENTS):
        raise _LiveManifestMismatch("unexpected requirement count")
    seen_ids: set[str] = set()
    for item, (expected_rule_type, expected_text) in zip(requirements, EXPECTED_REQUIREMENTS):
        if item.get("rule_type") != expected_rule_type:
            raise _LiveManifestMismatch("unexpected requirement rule_type")
        if _normalize_requirement_text(str(item.get("text", ""))) != expected_text:
            raise _LiveManifestMismatch("unexpected requirement text")
        requirement_id = item.get("requirement_id")
        if requirement_id in seen_ids:
            raise _LiveManifestMismatch("duplicate requirement id")
        seen_ids.add(requirement_id)


def _decimal_str(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format_decimal(value)
    return value


def _build_migration_output(
    *,
    run_id: str,
    source_data_path: Path,
    target_schema_path: Path,
    migration_result: Any,
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "mode": "live",
        "source_data_sha256": _sha256_path(source_data_path),
        "target_schema_sha256": _sha256_path(target_schema_path),
        "migrated_records": [
            {key: _decimal_str(value) for key, value in record.items()}
            for record in migration_result.migrated_records
        ],
        "rejected_records": [dict(record) for record in migration_result.rejected_records],
        "branch_balances": [
            {
                "branch": balance.branch,
                "debit_total": format_decimal(balance.debit_total),
                "credit_total": format_decimal(balance.credit_total),
                "difference": format_decimal(balance.difference),
            }
            for balance in migration_result.branch_balances
        ],
        "checks": sorted(checks, key=lambda check: check["test_id"]),
    }


def _build_task_context(
    *,
    implementation_doc_text: str,
    normalized_manifest: dict[str, Any],
    failure_payloads: list[dict[str, Any]],
    migration_output_path: Path,
) -> str:
    payload = {
        "implementation_doc": implementation_doc_text,
        "control_manifest": normalized_manifest,
        "failures": failure_payloads,
        "migration_test_output_path": _repo_relative_posix(migration_output_path),
        "goal": CODEX_GOAL,
        "required_outcomes": list(REQUIRED_OUTCOMES),
        "forbidden_changes": list(FORBIDDEN_CHANGES),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _salvage_quarantine_artifacts(
    store: Store, run_id: str, created_at: str, patch_id: str | None
) -> None:
    candidates: list[tuple[Path, str, str, str]] = [
        (config.QUARANTINE_DIR / "llm" / run_id / "control_manifest.raw.json", "raw_model_output", "gpt-5.6", "LiveLLMClient"),
    ]
    if patch_id is not None:
        codex_dir = config.QUARANTINE_DIR / "codex" / run_id / patch_id / "001"
        candidates.append((codex_dir / "proposal.raw.json", "raw_model_output", "codex", "LiveCodexClient"))
        candidates.append((codex_dir / "events.jsonl", "log", "codex", "LiveCodexClient"))
        candidates.append((codex_dir / "stderr.log", "log", "codex", "LiveCodexClient"))

    existing_paths = {artifact.path for artifact in store.list_artifacts(run_id)}
    for path, kind, producer, client in candidates:
        if not path.is_file():
            continue
        relative = _repo_relative_posix(path)
        if relative in existing_paths:
            continue
        artifact_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store,
            artifact_id=artifact_id,
            run_id=run_id,
            kind=kind,
            path=path,
            producer=producer,
            mode="live",
            client=client,
            validation_status="quarantined",
            created_at=created_at,
        )


def _fail_run(store: Store, run_id: str, stage: str, actor: str, created_at: str, patch_id: str | None) -> None:
    _salvage_quarantine_artifacts(store, run_id, created_at, patch_id)
    run = store.get_run(run_id)
    if run is not None and run.state != "FAILED":
        transition_run(store, run_id, "FAILED", actor)


def _safe_stage_message(stage: str) -> str:
    return f"live pipeline failed during stage: {stage}"


def run_live_pipeline(
    store: Store,
    *,
    validated: ValidatedLiveInputs,
    llm_client: Any,
    codex_client: Any,
    actor: str = "api",
) -> RunRow:
    run_id = store.allocate_id("RUN", start=2)
    run = store.create_run("live", config.SCHEMA_VERSION, state="CREATED", run_id=run_id)
    created_at = run.created_at

    stage = "ingest"
    patch_id: str | None = None
    try:
        doc_art_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store, artifact_id=doc_art_id, run_id=run_id, kind="input", path=validated.implementation_doc_path,
            producer="deterministic", mode="live", client="none", validation_status="not_required", created_at=created_at,
        )
        csv_art_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store, artifact_id=csv_art_id, run_id=run_id, kind="input", path=validated.source_data_path,
            producer="deterministic", mode="live", client="none", validation_status="not_required", created_at=created_at,
        )
        schema_art_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store, artifact_id=schema_art_id, run_id=run_id, kind="input", path=validated.target_schema_path,
            producer="deterministic", mode="live", client="none", validation_status="not_required", created_at=created_at,
        )
        transition_run(store, run_id, "INGESTED", actor)

        stage = "manifest"
        raw_manifest = llm_client.extract_requirements(
            implementation_doc=validated.implementation_doc_text,
            run_id=run_id,
            source_artifact_ids=[doc_art_id],
        )
        raw_manifest_path = config.QUARANTINE_DIR / "llm" / run_id / "control_manifest.raw.json"
        raw_manifest_art_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store, artifact_id=raw_manifest_art_id, run_id=run_id, kind="raw_model_output", path=raw_manifest_path,
            producer="gpt-5.6", mode="live", client="LiveLLMClient", validation_status="quarantined", created_at=created_at,
        )

        _validate_manifest_requirements(list(raw_manifest["requirements"]))

        req_ids = store.allocate_ids("REQ", 3, start=4)
        normalized_manifest = deepcopy(raw_manifest)
        for item, new_id in zip(normalized_manifest["requirements"], req_ids):
            item["requirement_id"] = new_id
        validate_output("control_manifest.schema.json", normalized_manifest)

        validated_manifest_path = config.LIVE_RUNS_DIR / run_id / "control_manifest.validated.json"
        _write_json(validated_manifest_path, normalized_manifest)
        validated_manifest_art_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store, artifact_id=validated_manifest_art_id, run_id=run_id, kind="validated_model_output",
            path=validated_manifest_path, producer="gpt-5.6", mode="live", client="LiveLLMClient",
            validation_status="validated", created_at=created_at,
        )

        for item in normalized_manifest["requirements"]:
            store.insert_requirement(
                RequirementRow(
                    requirement_id=item["requirement_id"],
                    run_id=run_id,
                    text=item["text"],
                    rule_type=item["rule_type"],
                    tolerance=item.get("tolerance"),
                    provenance=item["provenance"],
                )
            )
        transition_run(store, run_id, "MANIFEST_READY", actor)

        stage = "tests_generated"
        test_ids = store.allocate_ids("TEST", 3, start=4)
        test_source_ids = [validated_manifest_art_id, csv_art_id, schema_art_id]
        test_provenance = _provenance(run_id, created_at, test_source_ids, "deterministic", "live", "none", "not_required")
        for req_item, test_id, name in zip(normalized_manifest["requirements"], test_ids, LIVE_TEST_NAMES):
            store.insert_test(
                TestRow(
                    test_id=test_id,
                    run_id=run_id,
                    requirement_id=req_item["requirement_id"],
                    name=name,
                    status="pending",
                    output_ref=None,
                    provenance=test_provenance,
                )
            )
        transition_run(store, run_id, "TESTS_GENERATED", actor)

        stage = "execute"
        check_result = run_live_checks(validated.source_records, validated.target_schema)
        fail_ids = store.allocate_ids("FAIL", 3, start=4)
        checks: list[dict[str, Any]] = []
        failure_payloads: list[dict[str, Any]] = []
        failure_provenance_source_ids: list[str] = []

        for i, (rule_type, _expected_text) in enumerate(EXPECTED_REQUIREMENTS):
            checks.append(
                {
                    "requirement_id": normalized_manifest["requirements"][i]["requirement_id"],
                    "test_id": test_ids[i],
                    "rule_type": rule_type,
                    "status": "failed",
                    "failure_ids": [fail_ids[i]],
                }
            )

        migration_output = _build_migration_output(
            run_id=run_id,
            source_data_path=validated.source_data_path,
            target_schema_path=validated.target_schema_path,
            migration_result=check_result.migration_result,
            checks=checks,
        )
        migration_output_path = config.LIVE_RUNS_DIR / run_id / "migration_test_output.json"
        _write_json(migration_output_path, migration_output)
        migration_output_art_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store, artifact_id=migration_output_art_id, run_id=run_id, kind="test_output", path=migration_output_path,
            producer="deterministic", mode="live", client="none", validation_status="not_required", created_at=created_at,
        )

        failure_provenance = _provenance(
            run_id, created_at, [migration_output_art_id], "deterministic", "live", "none", "not_required"
        )
        for i, check_failure in enumerate(check_result.failures):
            requirement_id = normalized_manifest["requirements"][i]["requirement_id"]
            payload = {
                "failure_id": fail_ids[i],
                "record_id": check_failure.record_id,
                "requirement_id": requirement_id,
                "field": check_failure.field,
                "expected": check_failure.expected,
                "actual": check_failure.actual,
                "severity": check_failure.severity,
                "record_hash": check_failure.record_hash,
                "provenance": failure_provenance,
            }
            validate_output("failed_record.schema.json", payload)
            failure_payloads.append(payload)
            store.insert_failure(
                FailureRow(
                    failure_id=payload["failure_id"],
                    run_id=run_id,
                    requirement_id=requirement_id,
                    test_id=test_ids[i],
                    record_id=payload["record_id"],
                    field=payload["field"],
                    expected=payload["expected"],
                    actual=payload["actual"],
                    severity=payload["severity"],
                    record_hash=payload["record_hash"],
                    provenance=payload["provenance"],
                )
            )

        for test_id in test_ids:
            store.set_test_result(test_id, "failed", migration_output_art_id)

        transition_run(store, run_id, "EXECUTED", actor)
        transition_run(store, run_id, "TRIAGED", actor)

        stage = "codex_proposal"
        patch_id = store.allocate_id("PATCH", start=2)
        task_context = _build_task_context(
            implementation_doc_text=validated.implementation_doc_text,
            normalized_manifest=normalized_manifest,
            failure_payloads=failure_payloads,
            migration_output_path=migration_output_path,
        )
        codex_request = CodexProposalRequest(
            repo_path=config.REPO_ROOT,
            run_id=run_id,
            patch_id=patch_id,
            failure_ids=tuple(fail_ids),
            allowed_paths=("reconcile/migration.py",),
            source_artifact_ids=(validated_manifest_art_id, migration_output_art_id),
            schema_version=config.SCHEMA_VERSION,
            created_at=created_at,
            task_context=task_context,
            attempt=1,
        )
        validated_proposal = codex_client.propose_patch(codex_request)

        codex_quarantine_dir = config.QUARANTINE_DIR / "codex" / run_id / patch_id / "001"
        proposal_raw_path = codex_quarantine_dir / "proposal.raw.json"
        events_path = codex_quarantine_dir / "events.jsonl"
        stderr_path = codex_quarantine_dir / "stderr.log"

        proposal_raw_art_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store, artifact_id=proposal_raw_art_id, run_id=run_id, kind="raw_model_output", path=proposal_raw_path,
            producer="codex", mode="live", client="LiveCodexClient", validation_status="quarantined", created_at=created_at,
        )
        events_art_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store, artifact_id=events_art_id, run_id=run_id, kind="log", path=events_path,
            producer="codex", mode="live", client="LiveCodexClient", validation_status="quarantined", created_at=created_at,
        )
        stderr_art_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store, artifact_id=stderr_art_id, run_id=run_id, kind="log", path=stderr_path,
            producer="codex", mode="live", client="LiveCodexClient", validation_status="quarantined", created_at=created_at,
        )

        validated_patch_path = config.LIVE_RUNS_DIR / run_id / f"{patch_id}.validated.json"
        _write_json(validated_patch_path, validated_proposal)
        validated_patch_art_id = store.allocate_id("ART", start=10)
        _persist_artifact(
            store, artifact_id=validated_patch_art_id, run_id=run_id, kind="patch_diff", path=validated_patch_path,
            producer="codex", mode="live", client="LiveCodexClient", validation_status="validated", created_at=created_at,
        )

        store.insert_patch(
            PatchRow(
                patch_id=patch_id,
                run_id=run_id,
                failure_ids=list(fail_ids),
                diff=validated_proposal["diff"],
                status="pending",
                approved_by=None,
                approved_at=None,
                applied_at=None,
                provenance=validated_proposal["provenance"],
            )
        )
        transition_run(store, run_id, "PATCH_PENDING", actor)
    except LivePipelineError:
        raise
    except Exception as error:
        _fail_run(store, run_id, stage, actor, created_at, patch_id)
        raise LivePipelineError(run_id, stage, _safe_stage_message(stage)) from error

    final_run = store.get_run(run_id)
    assert final_run is not None
    return final_run
