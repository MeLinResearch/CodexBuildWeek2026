import hashlib
import json

from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.store.db import Store

client = TestClient(app)


def test_fixture_endpoints_without_openai_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    db_path = tmp_path / "api.sqlite"
    live_runs = config.REPO_ROOT / ".release_assurance/tests" / tmp_path.name
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "LIVE_RUNS_DIR", live_runs)
    target = config.REPO_ROOT / "reconcile/migration.py"
    target_before = target.read_bytes()

    assert client.post("/api/runs", json={"mode": "fixture", "fixture_set": "bank_migration_demo_v1"}).json() == {"run_id": "RUN-001"}
    assert client.get("/api/runs/RUN-001").status_code == 200
    assert client.get("/api/runs/RUN-001/matrix").status_code == 200
    assert client.get("/api/runs/RUN-001/failures/FAIL-001").status_code == 200
    assert client.get("/api/runs/RUN-001/patches").status_code == 200
    assert client.get("/api/patches/PATCH-001").status_code == 200
    assert client.post("/api/patches/PATCH-001/approve", json={"actor": "demo_user", "note": "optional"}).json()["status"] == "approved"
    assert client.post("/api/patches/PATCH-001/reject", json={"actor": "demo_user", "note": "optional"}).status_code == 409
    rerun = client.post("/api/runs/RUN-001/rerun")
    assert rerun.status_code == 200
    assert rerun.json()["state"] == "EVIDENCE_READY"
    store = Store(db_path)
    patch = store.get_patch("PATCH-001")
    assert patch is not None and patch.status == "applied"
    tests = store.list_tests("RUN-001")
    assert all(test.status == "passed" for test in tests)
    rerun_artifact_id = tests[0].output_ref
    assert rerun_artifact_id is not None
    assert all(test.output_ref == rerun_artifact_id for test in tests)
    matrix = client.get("/api/runs/RUN-001/matrix").json()
    assert all(row["row_status"] == "rerun_passed" for row in matrix)
    assert all(row["evidence_refs"] == [rerun_artifact_id] for row in matrix)
    assert all(
        not {"ART-006", "ART-007", "ART-008"}.intersection(row["evidence_refs"])
        for row in matrix
    )
    report = json.loads((live_runs / "RUN-001/rerun_result.json").read_text())
    assert report["artifact_id"] == rerun_artifact_id
    assert report["checks"] == {
        "account_identifiers": "passed",
        "invalid_dates": "passed",
        "branch_balance": "passed",
    }
    assert target.read_bytes() == target_before
    evidence = client.get("/api/runs/RUN-001/evidence")
    assert evidence.status_code == 200
    assert "Fixture evidence, no live model calls" in evidence.text


def test_fixture_rerun_rejects_patch_that_leaves_a_defect(monkeypatch, tmp_path):
    db_path = tmp_path / "api.sqlite"
    live_runs = config.REPO_ROOT / ".release_assurance/tests" / tmp_path.name
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "LIVE_RUNS_DIR", live_runs)
    target = config.REPO_ROOT / "reconcile/migration.py"
    target_before = hashlib.sha256(target.read_bytes()).hexdigest()

    client.post("/api/runs", json={"mode": "fixture", "fixture_set": "bank_migration_demo_v1"})
    store = Store(db_path, clock=config.fixture_clock)
    patch = store.get_patch("PATCH-001")
    assert patch is not None
    incomplete_diff = patch.diff.replace("+        return -amount", "+        return amount")
    assert incomplete_diff != patch.diff
    with store.connect() as connection:
        connection.execute(
            "UPDATE patches SET diff = ? WHERE patch_id = ?",
            (incomplete_diff, "PATCH-001"),
        )
    original_output_refs = {
        test.test_id: test.output_ref for test in store.list_tests("RUN-001")
    }
    client.post(
        "/api/patches/PATCH-001/approve",
        json={"actor": "demo_user", "note": "negative verification case"},
    )

    response = client.post("/api/runs/RUN-001/rerun")

    assert response.status_code == 422
    failed_store = Store(db_path)
    assert failed_store.get_run("RUN-001").state == "FAILED"
    assert failed_store.get_patch("PATCH-001").status == "apply_failed"
    failed_tests = failed_store.list_tests("RUN-001")
    assert all(test.status == "failed" for test in failed_tests)
    assert {
        test.test_id: test.output_ref for test in failed_tests
    } == original_output_refs
    matrix = client.get("/api/runs/RUN-001/matrix").json()
    assert all(row["row_status"] != "rerun_passed" for row in matrix)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == target_before


def test_unknown_ids_404(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "api.sqlite")

    assert client.get("/api/runs/RUN-999").status_code == 404
    assert client.get("/api/patches/PATCH-999").status_code == 404
    assert client.get("/api/runs/RUN-001/failures/FAIL-999").status_code == 404
