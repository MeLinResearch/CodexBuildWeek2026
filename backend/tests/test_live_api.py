from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.routers import runs as runs_router

client = TestClient(app)

LIVE_REQUEST = {
    "mode": "live",
    "implementation_doc_path": "fixtures/implementation_doc.md",
    "source_data_path": "fixtures/source_data/accounts.csv",
    "target_schema_path": "fixtures/schemas/target_schema.json",
}

FAKE_CODEX_DIFF = (
    "diff --git a/reconcile/migration.py b/reconcile/migration.py\n"
    "--- a/reconcile/migration.py\n"
    "+++ b/reconcile/migration.py\n"
    "@@ -1 +1 @@\n"
    "-a\n"
    "+b\n"
)


def _use_tmp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "api.sqlite"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    return db_path


def _isolate_live_dirs(monkeypatch, tmp_path):
    quarantine_root = config.REPO_ROOT / ".release_assurance" / "test_tmp" / tmp_path.name / "quarantine"
    runs_root = config.REPO_ROOT / ".release_assurance" / "test_tmp" / tmp_path.name / "runs"
    monkeypatch.setattr(config, "QUARANTINE_DIR", quarantine_root)
    monkeypatch.setattr(config, "LIVE_RUNS_DIR", runs_root)
    return quarantine_root, runs_root


class FakeLiveLLMClient:
    def __init__(self, quarantine_root: Path) -> None:
        self.quarantine_root = quarantine_root

    def extract_requirements(self, *, implementation_doc, run_id, source_artifact_ids):
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
                    "text": "preserve account identifiers verbatim",
                    "provenance": provenance,
                },
                {
                    "requirement_id": "REQ-002",
                    "rule_type": "balancing_rule",
                    "text": "debits equal credits by branch",
                    "provenance": provenance,
                },
                {
                    "requirement_id": "REQ-003",
                    "rule_type": "exception_handling",
                    "text": "no silent value substitution",
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

    def propose_patch(self, request):
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


def _patch_live_clients(monkeypatch, tmp_path):
    quarantine_root, _runs_root = _isolate_live_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(runs_router, "_make_live_llm_client", lambda: FakeLiveLLMClient(quarantine_root))
    monkeypatch.setattr(runs_router, "_make_live_codex_client", lambda: FakeLiveCodexClient(quarantine_root))


def _forbid_live_clients(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("live client must not be constructed")

    monkeypatch.setattr(runs_router, "_make_live_llm_client", fail)
    monkeypatch.setattr(runs_router, "_make_live_codex_client", fail)


def test_post_fixture_returns_run_001_and_makes_no_live_calls(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _forbid_live_clients(monkeypatch)

    response = client.post("/api/runs", json={"mode": "fixture", "fixture_set": "bank_migration_demo_v1"})
    assert response.status_code == 200
    assert response.json() == {"run_id": "RUN-001"}


def test_post_live_with_canonical_paths_returns_allocated_run_id(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _patch_live_clients(monkeypatch, tmp_path)

    response = client.post("/api/runs", json=LIVE_REQUEST)

    assert response.status_code == 200
    assert response.json() == {"run_id": "RUN-002"}


def test_post_live_missing_paths_returns_400_without_model_calls(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _forbid_live_clients(monkeypatch)

    response = client.post("/api/runs", json={"mode": "live"})
    assert response.status_code == 400


def test_post_live_unsafe_paths_return_400_without_model_calls(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _forbid_live_clients(monkeypatch)

    absolute_path_request = dict(LIVE_REQUEST)
    absolute_path_request["implementation_doc_path"] = "/etc/passwd"
    response = client.post("/api/runs", json=absolute_path_request)
    assert response.status_code == 400

    traversal_request = dict(LIVE_REQUEST)
    traversal_request["source_data_path"] = "../fixtures/source_data/accounts.csv"
    response = client.post("/api/runs", json=traversal_request)
    assert response.status_code == 400


def test_post_live_rejects_fixture_set(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _forbid_live_clients(monkeypatch)

    bad_request = dict(LIVE_REQUEST)
    bad_request["fixture_set"] = "bank_migration_demo_v1"
    response = client.post("/api/runs", json=bad_request)
    assert response.status_code == 400


def test_live_run_fetch_endpoints_use_dynamic_ids(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _patch_live_clients(monkeypatch, tmp_path)

    run_id = client.post("/api/runs", json=LIVE_REQUEST).json()["run_id"]
    assert run_id == "RUN-002"

    run_response = client.get(f"/api/runs/{run_id}")
    assert run_response.status_code == 200
    assert run_response.json()["mode"] == "live"
    assert run_response.json()["state"] == "PATCH_PENDING"

    matrix = client.get(f"/api/runs/{run_id}/matrix").json()
    assert len(matrix) == 3
    assert all(row["patch_id"] == "PATCH-002" for row in matrix)
    failure_id = matrix[0]["failure_ids"][0]

    failure_response = client.get(f"/api/runs/{run_id}/failures/{failure_id}")
    assert failure_response.status_code == 200

    patches_response = client.get(f"/api/runs/{run_id}/patches")
    assert patches_response.status_code == 200
    assert patches_response.json()[0]["patch_id"] == "PATCH-002"

    patch_detail = client.get("/api/patches/PATCH-002")
    assert patch_detail.status_code == 200
    assert patch_detail.json()["status"] == "pending"

    evidence_response = client.get(f"/api/runs/{run_id}/evidence")
    assert evidence_response.status_code == 200
    assert "RUN-002" in evidence_response.text
    assert "PATCH-002" in evidence_response.text


def test_approve_live_dynamic_patch_reaches_patch_approved(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _patch_live_clients(monkeypatch, tmp_path)

    run_id = client.post("/api/runs", json=LIVE_REQUEST).json()["run_id"]

    response = client.post("/api/patches/PATCH-002/approve", json={"actor": "demo_user", "note": "ok"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    assert client.get(f"/api/runs/{run_id}").json()["state"] == "PATCH_APPROVED"
    assert client.get("/api/patches/PATCH-002").json()["status"] == "approved"


def test_live_rerun_returns_501_and_leaves_state_unchanged(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _patch_live_clients(monkeypatch, tmp_path)

    run_id = client.post("/api/runs", json=LIVE_REQUEST).json()["run_id"]
    client.post("/api/patches/PATCH-002/approve", json={"actor": "demo_user", "note": "ok"})

    response = client.post(f"/api/runs/{run_id}/rerun")
    assert response.status_code == 501

    assert client.get(f"/api/runs/{run_id}").json()["state"] == "PATCH_APPROVED"
    assert client.get("/api/patches/PATCH-002").json()["status"] == "approved"


def test_fixture_approval_and_rerun_behavior_unchanged(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    assert client.post(
        "/api/runs", json={"mode": "fixture", "fixture_set": "bank_migration_demo_v1"}
    ).json() == {"run_id": "RUN-001"}
    approve = client.post("/api/patches/PATCH-001/approve", json={"actor": "demo_user", "note": "ok"})
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    rerun = client.post("/api/runs/RUN-001/rerun")
    assert rerun.status_code == 200
    assert rerun.json() == {
        "run_id": "RUN-001",
        "status": "rerun complete",
        "state": "EVIDENCE_READY",
        "mode": "fixture",
    }
