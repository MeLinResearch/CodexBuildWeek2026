from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.store.db import Store
from app.store.models import ArtifactRow, PatchRow

client = TestClient(app)


def _live_provenance() -> dict:
    return {"schema_version": config.SCHEMA_VERSION, "run_id": "RUN-002",
            "created_at": "2026-07-17T00:00:00Z", "source_artifact_ids": ["ART-010"],
            "producer": "codex", "mode": "live", "client": "LiveCodexClient",
            "validation_status": "validated"}


def _prepare(monkeypatch, tmp_path: Path, *, incomplete: bool = False):
    db_path = tmp_path / "store.db"
    live_runs = config.REPO_ROOT / ".release_assurance/tests" / tmp_path.name
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "LIVE_RUNS_DIR", live_runs)
    store = Store(db_path, clock=lambda: "2026-07-17T00:00:00Z")
    store.init_schema()
    store.create_run("live", config.SCHEMA_VERSION, state="PATCH_APPROVED", run_id="RUN-002")
    source = config.FIXTURES_DIR / "source_data/accounts.csv"
    store.insert_artifact(ArtifactRow("ART-010", "RUN-002", "input",
        source.relative_to(config.REPO_ROOT).as_posix(), hashlib.sha256(source.read_bytes()).hexdigest(),
        "deterministic", "live", "none", "not_required", "2026-07-17T00:00:00Z"))
    proposal = json.loads((config.FIXTURES_DIR / "api/patch_PATCH-001.fixture.json").read_text())
    diff = proposal["diff"]
    if incomplete:
        diff = diff.replace("+        return -amount", "+        return amount")
    store.insert_patch(PatchRow("PATCH-002", "RUN-002", ["FAIL-004", "FAIL-005", "FAIL-006"],
                                diff, "approved", "melinda.emerson",
                                "2026-07-17T00:00:00Z", None, _live_provenance()))
    return db_path, live_runs


def test_live_rerun_applies_only_in_disposable_workspace(monkeypatch, tmp_path: Path):
    db_path, live_runs = _prepare(monkeypatch, tmp_path)
    target = config.REPO_ROOT / "reconcile/migration.py"
    before = hashlib.sha256(target.read_bytes()).hexdigest()

    response = client.post("/api/runs/RUN-002/rerun")

    assert response.status_code == 200
    assert response.json() == {"run_id": "RUN-002", "status": "rerun complete",
                               "state": "EVIDENCE_READY", "mode": "live"}
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before
    completed = Store(db_path).get_patch("PATCH-002")
    assert completed is not None and completed.status == "applied"
    report = json.loads((live_runs / "RUN-002/rerun_result.json").read_text())
    assert report["status"] == "passed"
    assert report["pre_apply_tree"] != report["post_apply_tree"]
    assert report["checks"] == {"account_identifiers": "passed", "invalid_dates": "passed",
                                 "branch_balance": "passed"}
    assert Store(db_path).get_run("RUN-002").state == "EVIDENCE_READY"


def test_live_rerun_failure_is_mechanical_and_persisted(monkeypatch, tmp_path: Path):
    db_path, _ = _prepare(monkeypatch, tmp_path, incomplete=True)

    response = client.post("/api/runs/RUN-002/rerun")

    assert response.status_code == 422
    store = Store(db_path)
    assert store.get_patch("PATCH-002").status == "apply_failed"
    assert store.get_run("RUN-002").state == "FAILED"
