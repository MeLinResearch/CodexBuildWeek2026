from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app import config
from app.pipeline.live_pipeline import (
    LiveInputError,
    LivePipelineError,
    LiveRunInputs,
    run_live_pipeline,
    validate_live_run_inputs,
)
from app.pipeline.mock_pipeline import run_fixture_pipeline
from app.store.db import Store

REPO_ROOT = config.REPO_ROOT
MIGRATION_PATH = REPO_ROOT / "reconcile" / "migration.py"

CANONICAL_INPUTS = LiveRunInputs(
    implementation_doc_path=Path("fixtures/implementation_doc.md"),
    source_data_path=Path("fixtures/source_data/accounts.csv"),
    target_schema_path=Path("fixtures/schemas/target_schema.json"),
)

FAKE_CODEX_DIFF = (
    "diff --git a/reconcile/migration.py b/reconcile/migration.py\n"
    "--- a/reconcile/migration.py\n"
    "+++ b/reconcile/migration.py\n"
    "@@ -1 +1 @@\n"
    "-a\n"
    "+b\n"
)


def _isolate_live_dirs(monkeypatch, tmp_path):
    quarantine_root = REPO_ROOT / ".release_assurance" / "test_tmp" / tmp_path.name / "quarantine"
    runs_root = REPO_ROOT / ".release_assurance" / "test_tmp" / tmp_path.name / "runs"
    monkeypatch.setattr(config, "QUARANTINE_DIR", quarantine_root)
    monkeypatch.setattr(config, "LIVE_RUNS_DIR", runs_root)
    return quarantine_root, runs_root


class FakeLiveLLMClient:
    def __init__(self, quarantine_root: Path) -> None:
        self.quarantine_root = quarantine_root
        self.calls: list[dict] = []

    def extract_requirements(self, *, implementation_doc, run_id, source_artifact_ids):
        self.calls.append({"run_id": run_id, "source_artifact_ids": list(source_artifact_ids)})
        created_at = "2026-07-17T00:00:00Z"
        provenance = {
            "schema_version": config.SCHEMA_VERSION,
            "run_id": run_id,
            "created_at": created_at,
            "source_artifact_ids": list(source_artifact_ids),
            "producer": "gpt-5.6",
            "mode": "live",
            "client": "LiveLLMClient",
            "validation_status": "validated",
        }
        payload = {
            "run_id": run_id,
            "provenance": provenance,
            "requirements": [
                {
                    "requirement_id": "REQ-001",
                    "rule_type": "field_validation",
                    "text": "Preserve account identifiers verbatim.",
                    "provenance": provenance,
                },
                {
                    "requirement_id": "REQ-002",
                    "rule_type": "balancing_rule",
                    "text": "Debits equal credits by branch.",
                    "provenance": provenance,
                },
                {
                    "requirement_id": "REQ-003",
                    "rule_type": "exception_handling",
                    "text": "No silent value substitution.",
                    "provenance": provenance,
                },
            ],
        }
        raw_path = self.quarantine_root / "llm" / run_id / "control_manifest.raw.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return payload


class FakeLiveCodexClient:
    def __init__(self, quarantine_root: Path) -> None:
        self.quarantine_root = quarantine_root
        self.calls: list = []

    def propose_patch(self, request):
        self.calls.append(request)
        quarantine = self.quarantine_root / "codex" / request.run_id / request.patch_id / f"{request.attempt:03d}"
        quarantine.mkdir(parents=True, exist_ok=True)
        (quarantine / "proposal.raw.json").write_text("raw-proposal", encoding="utf-8")
        (quarantine / "events.jsonl").write_text("events\n", encoding="utf-8")
        (quarantine / "stderr.log").write_text("", encoding="utf-8")
        provenance = {
            "schema_version": request.schema_version,
            "run_id": request.run_id,
            "created_at": request.created_at,
            "source_artifact_ids": list(request.source_artifact_ids),
            "producer": "codex",
            "mode": "live",
            "client": "LiveCodexClient",
            "validation_status": "validated",
        }
        return {
            "patch_id": request.patch_id,
            "run_id": request.run_id,
            "failure_ids": list(request.failure_ids),
            "diff": FAKE_CODEX_DIFF,
            "status": "pending",
            "provenance": provenance,
        }


class FailingLiveLLMClient:
    def __init__(self, quarantine_root: Path) -> None:
        self.quarantine_root = quarantine_root

    def extract_requirements(self, *, implementation_doc, run_id, source_artifact_ids):
        raw_path = self.quarantine_root / "llm" / run_id / "control_manifest.raw.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text("not json", encoding="utf-8")
        raise RuntimeError("simulated GPT boundary failure: secret-token-xyz")


class FailingLiveCodexClient:
    def __init__(self, quarantine_root: Path) -> None:
        self.quarantine_root = quarantine_root

    def propose_patch(self, request):
        quarantine = self.quarantine_root / "codex" / request.run_id / request.patch_id / f"{request.attempt:03d}"
        quarantine.mkdir(parents=True, exist_ok=True)
        (quarantine / "proposal.raw.json").write_text("bad json", encoding="utf-8")
        (quarantine / "events.jsonl").write_text("events\n", encoding="utf-8")
        (quarantine / "stderr.log").write_text("stderr output sk-secretvalue", encoding="utf-8")
        raise RuntimeError("simulated Codex execution failure")


def _store(tmp_path):
    return Store(tmp_path / "pipeline.sqlite", clock=lambda: "2026-07-17T00:00:00Z")


def test_validate_live_run_inputs_accepts_canonical_paths():
    validated = validate_live_run_inputs(CANONICAL_INPUTS)
    assert len(validated.source_records) == 4
    assert validated.target_schema["type"] == "object"
    assert validated.implementation_doc_text.strip()


def test_validate_live_run_inputs_rejects_absolute_path():
    bad = LiveRunInputs(
        implementation_doc_path=Path("/etc/passwd"),
        source_data_path=CANONICAL_INPUTS.source_data_path,
        target_schema_path=CANONICAL_INPUTS.target_schema_path,
    )
    with pytest.raises(LiveInputError):
        validate_live_run_inputs(bad)


def test_validate_live_run_inputs_rejects_traversal():
    bad = LiveRunInputs(
        implementation_doc_path=Path("fixtures/../fixtures/implementation_doc.md"),
        source_data_path=CANONICAL_INPUTS.source_data_path,
        target_schema_path=CANONICAL_INPUTS.target_schema_path,
    )
    with pytest.raises(LiveInputError):
        validate_live_run_inputs(bad)


def test_validate_live_run_inputs_rejects_path_outside_fixtures():
    bad = LiveRunInputs(
        implementation_doc_path=Path("ARCHITECTURE.md"),
        source_data_path=CANONICAL_INPUTS.source_data_path,
        target_schema_path=CANONICAL_INPUTS.target_schema_path,
    )
    with pytest.raises(LiveInputError):
        validate_live_run_inputs(bad)


def test_successful_live_pipeline(monkeypatch, tmp_path):
    quarantine_root, _runs_root = _isolate_live_dirs(monkeypatch, tmp_path)
    s = _store(tmp_path)
    s.init_schema()
    run_fixture_pipeline(s)  # seed fixture data first

    validated = validate_live_run_inputs(CANONICAL_INPUTS)
    llm_client = FakeLiveLLMClient(quarantine_root)
    codex_client = FakeLiveCodexClient(quarantine_root)

    migration_hash_before = hashlib.sha256(MIGRATION_PATH.read_bytes()).hexdigest()

    run = run_live_pipeline(
        s, validated=validated, llm_client=llm_client, codex_client=codex_client, actor="api_test"
    )

    migration_hash_after = hashlib.sha256(MIGRATION_PATH.read_bytes()).hexdigest()
    assert migration_hash_before == migration_hash_after

    assert run.run_id == "RUN-002"
    assert run.state == "PATCH_PENDING"
    assert run.mode == "live"

    requirements = s.list_requirements("RUN-002")
    assert [r.requirement_id for r in requirements] == ["REQ-004", "REQ-005", "REQ-006"]

    tests = s.list_tests("RUN-002")
    assert [t.test_id for t in tests] == ["TEST-004", "TEST-005", "TEST-006"]
    assert all(t.status == "failed" for t in tests)
    assert len({t.output_ref for t in tests}) == 1

    failures = s.list_failures("RUN-002")
    assert [f.failure_id for f in failures] == ["FAIL-004", "FAIL-005", "FAIL-006"]
    failures_by_id = {f.failure_id: f for f in failures}
    assert failures_by_id["FAIL-004"].expected == "00012345"
    assert failures_by_id["FAIL-004"].actual == "12345"
    assert failures_by_id["FAIL-005"].expected == "Branch 101 debits 1250.00 credits 1200.00 diff 50.00"
    assert failures_by_id["FAIL-005"].actual == "50.00"
    assert failures_by_id["FAIL-006"].expected == "reject unparseable date"
    assert failures_by_id["FAIL-006"].actual == "1900-01-01"

    patches = s.list_patches("RUN-002")
    assert len(patches) == 1
    patch = patches[0]
    assert patch.patch_id == "PATCH-002"
    assert patch.status == "pending"
    assert patch.approved_by is None
    assert patch.approved_at is None
    assert patch.applied_at is None
    assert patch.failure_ids == ["FAIL-004", "FAIL-005", "FAIL-006"]

    transitions = s.list_state_transitions("RUN-002")
    assert [(t.from_state, t.to_state) for t in transitions] == [
        ("CREATED", "INGESTED"),
        ("INGESTED", "MANIFEST_READY"),
        ("MANIFEST_READY", "TESTS_GENERATED"),
        ("TESTS_GENERATED", "EXECUTED"),
        ("EXECUTED", "TRIAGED"),
        ("TRIAGED", "PATCH_PENDING"),
    ]
    assert all(t.actor == "api_test" for t in transitions)

    artifacts = s.list_artifacts("RUN-002")
    assert [a.artifact_id for a in artifacts] == [f"ART-{n:03d}" for n in range(10, 20)]
    for artifact in artifacts:
        full_path = REPO_ROOT / artifact.path
        assert full_path.is_file()
        assert artifact.sha256 == hashlib.sha256(full_path.read_bytes()).hexdigest()
        assert artifact.mode == "live"

    by_id = {a.artifact_id: a for a in artifacts}
    assert by_id["ART-010"].kind == "input"
    assert by_id["ART-010"].validation_status == "not_required"
    assert by_id["ART-013"].kind == "raw_model_output"
    assert by_id["ART-013"].validation_status == "quarantined"
    assert by_id["ART-014"].kind == "validated_model_output"
    assert by_id["ART-014"].validation_status == "validated"
    assert by_id["ART-015"].kind == "test_output"
    assert by_id["ART-019"].kind == "patch_diff"
    assert by_id["ART-019"].validation_status == "validated"

    codex_call = codex_client.calls[0]
    assert codex_call.allowed_paths == ("reconcile/migration.py",)
    assert codex_call.failure_ids == ("FAIL-004", "FAIL-005", "FAIL-006")

    # fixture run remains intact
    fixture_run = s.get_run("RUN-001")
    assert fixture_run.state == "PATCH_PENDING"
    assert [r.requirement_id for r in s.list_requirements("RUN-001")] == ["REQ-001", "REQ-002", "REQ-003"]
    assert [p.patch_id for p in s.list_patches("RUN-001")] == ["PATCH-001"]


def test_gpt_failure_preserves_raw_output_and_fails_run(monkeypatch, tmp_path):
    quarantine_root, _runs_root = _isolate_live_dirs(monkeypatch, tmp_path)
    s = _store(tmp_path)
    s.init_schema()

    validated = validate_live_run_inputs(CANONICAL_INPUTS)
    llm_client = FailingLiveLLMClient(quarantine_root)
    codex_client = FakeLiveCodexClient(quarantine_root)

    with pytest.raises(LivePipelineError) as excinfo:
        run_live_pipeline(s, validated=validated, llm_client=llm_client, codex_client=codex_client, actor="api_test")

    error = excinfo.value
    assert error.run_id == "RUN-002"
    assert error.stage == "manifest"
    assert "secret-token-xyz" not in str(error)

    run = s.get_run("RUN-002")
    assert run.state == "FAILED"

    artifacts = s.list_artifacts("RUN-002")
    raw_artifacts = [a for a in artifacts if a.kind == "raw_model_output"]
    assert len(raw_artifacts) == 1
    assert raw_artifacts[0].validation_status == "quarantined"
    assert (REPO_ROOT / raw_artifacts[0].path).is_file()

    assert s.list_patches("RUN-002") == []


def test_codex_failure_preserves_raw_files_and_fails_run_without_pending_patch(monkeypatch, tmp_path):
    quarantine_root, _runs_root = _isolate_live_dirs(monkeypatch, tmp_path)
    s = _store(tmp_path)
    s.init_schema()

    validated = validate_live_run_inputs(CANONICAL_INPUTS)
    llm_client = FakeLiveLLMClient(quarantine_root)
    codex_client = FailingLiveCodexClient(quarantine_root)

    with pytest.raises(LivePipelineError) as excinfo:
        run_live_pipeline(s, validated=validated, llm_client=llm_client, codex_client=codex_client, actor="api_test")

    error = excinfo.value
    assert error.run_id == "RUN-002"
    assert error.stage == "codex_proposal"
    assert "sk-secretvalue" not in str(error)

    run = s.get_run("RUN-002")
    assert run.state == "FAILED"

    artifacts = s.list_artifacts("RUN-002")
    log_artifacts = [a for a in artifacts if a.kind == "log"]
    assert len(log_artifacts) == 2
    codex_raw_artifacts = [a for a in artifacts if a.kind == "raw_model_output" and "/codex/" in a.path]
    assert len(codex_raw_artifacts) == 1
    llm_raw_artifacts = [a for a in artifacts if a.kind == "raw_model_output" and "/llm/" in a.path]
    assert len(llm_raw_artifacts) == 1

    assert s.list_patches("RUN-002") == []
