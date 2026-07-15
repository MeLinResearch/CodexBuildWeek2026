from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.store.db import Store

client = TestClient(app)


def _use_tmp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "api.sqlite"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    return db_path


def _post_fixture():
    response = client.post("/api/runs", json={"mode": "fixture", "fixture_set": "bank_migration_demo_v1"})
    assert response.status_code == 200
    assert response.json() == {"run_id": "RUN-001"}
    return response


def test_post_populates_store(monkeypatch, tmp_path):
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()

    store = Store(db_path)
    run = store.get_run("RUN-001")
    assert run is not None
    assert run.state == "PATCH_PENDING"
    assert len(store.list_requirements("RUN-001")) == 3
    assert len(store.list_tests("RUN-001")) == 3
    assert len(store.list_failures("RUN-001")) == 3
    assert len(store.list_patches("RUN-001")) == 1
    assert len(store.list_artifacts("RUN-001")) == 6


def test_get_run_reflects_store(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()

    payload = client.get("/api/runs/RUN-001").json()
    assert payload["state"] == "PATCH_PENDING"
    assert payload["mode"] == "fixture"
    assert payload["schema_version"] == "2026-07-12.1"
    assert payload["provenance"]["client"] == "FixtureLLMClient"


def test_matrix_endpoint_is_built_from_store(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()

    payload = client.get("/api/runs/RUN-001/matrix").json()
    comparable = [
        {key: row[key] for key in ["requirement_id", "test_id", "failure_ids", "patch_id", "row_status", "evidence_refs"]}
        for row in payload
    ]
    assert comparable == [
        {
            "requirement_id": "REQ-001",
            "test_id": "TEST-001",
            "failure_ids": ["FAIL-001"],
            "patch_id": "PATCH-001",
            "row_status": "patch_pending",
            "evidence_refs": ["ART-006"],
        },
        {
            "requirement_id": "REQ-002",
            "test_id": "TEST-002",
            "failure_ids": ["FAIL-002"],
            "patch_id": "PATCH-001",
            "row_status": "patch_pending",
            "evidence_refs": ["ART-007"],
        },
        {
            "requirement_id": "REQ-003",
            "test_id": "TEST-003",
            "failure_ids": ["FAIL-003"],
            "patch_id": "PATCH-001",
            "row_status": "patch_pending",
            "evidence_refs": ["ART-008"],
        },
    ]


def test_failure_endpoint_omits_store_only_fields(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()

    payload = client.get("/api/runs/RUN-001/failures/FAIL-001").json()
    assert set(payload) == {
        "failure_id",
        "record_id",
        "requirement_id",
        "field",
        "expected",
        "actual",
        "severity",
        "record_hash",
        "provenance",
    }
    assert "run_id" not in payload
    assert "test_id" not in payload


def test_patch_endpoints_are_store_backed(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()

    patches_payload = client.get("/api/runs/RUN-001/patches").json()
    patch_payload = client.get("/api/patches/PATCH-001").json()
    assert patches_payload[0]["patch_id"] == "PATCH-001"
    assert patches_payload[0]["status"] == "pending"
    assert patches_payload[0]["failure_ids"] == ["FAIL-001", "FAIL-002", "FAIL-003"]
    assert patch_payload["patch_id"] == "PATCH-001"
    assert patch_payload["status"] == "pending"
    assert patch_payload["failure_ids"] == ["FAIL-001", "FAIL-002", "FAIL-003"]


def test_evidence_uses_store_data(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()

    html = client.get("/api/runs/RUN-001/evidence").text
    for expected in [
        "Release Assurance Evidence Pack",
        "<dt>run_id</dt><dd>RUN-001</dd>",
        "<dt>mode</dt><dd>fixture</dd>",
        "preserve account identifiers verbatim",
        "debits equal credits by branch",
        "no silent value substitution",
        "FAIL-001",
        "FAIL-002",
        "FAIL-003",
        "PATCH-001",
        "Fixture evidence, no live model calls",
    ]:
        assert expected in html


def test_unknown_ids_still_404(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    assert client.get("/api/runs/RUN-999").status_code == 404
    assert client.get("/api/patches/PATCH-999").status_code == 404
    _post_fixture()
    assert client.get("/api/runs/RUN-001/failures/FAIL-999").status_code == 404


def test_no_live_env_needed(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    _post_fixture()
    assert client.get("/api/runs/RUN-001").status_code == 200


def _matrix_statuses():
    return {row["row_status"] for row in client.get("/api/runs/RUN-001/matrix").json()}


def test_approval_persists_patch_status_run_state_and_matrix(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()
    assert client.get("/api/runs/RUN-001").json()["state"] == "PATCH_PENDING"

    response = client.post(
        "/api/patches/PATCH-001/approve",
        json={"actor": "demo_user", "note": "looks good"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "patch_id": "PATCH-001",
        "status": "approved",
        "actor": "demo_user",
        "note": "looks good",
    }
    assert client.get("/api/patches/PATCH-001").json()["status"] == "approved"
    assert client.get("/api/runs/RUN-001").json()["state"] == "PATCH_APPROVED"
    assert _matrix_statuses() == {"patch_approved"}
    assert "approved" not in _matrix_statuses()
    assert client.post(
        "/api/patches/PATCH-001/approve",
        json={"actor": "demo_user", "note": "again"},
    ).status_code == 409
    assert client.post(
        "/api/patches/PATCH-001/reject",
        json={"actor": "demo_user", "note": "nope"},
    ).status_code == 409


def test_rejection_persists_patch_status_run_state_and_matrix(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()

    response = client.post(
        "/api/patches/PATCH-001/reject",
        json={"actor": "demo_user", "note": "not safe"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "patch_id": "PATCH-001",
        "status": "rejected",
        "actor": "demo_user",
        "note": "not safe",
    }
    assert client.get("/api/patches/PATCH-001").json()["status"] == "rejected"
    assert client.get("/api/runs/RUN-001").json()["state"] == "PATCH_REJECTED"
    assert _matrix_statuses() == {"failed"}


def test_unknown_patch_approval_returns_404(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()

    response = client.post(
        "/api/patches/PATCH-404/approve",
        json={"actor": "demo_user", "note": "missing"},
    )

    assert response.status_code == 404


def test_rerun_requires_approval_then_persists_evidence_ready_and_applied(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()
    assert client.post("/api/runs/RUN-001/rerun").status_code == 409
    client.post(
        "/api/patches/PATCH-001/approve",
        json={"actor": "demo_user", "note": "ready"},
    )

    response = client.post("/api/runs/RUN-001/rerun")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": "RUN-001",
        "status": "rerun complete",
        "state": "EVIDENCE_READY",
        "mode": "fixture",
    }
    assert client.get("/api/runs/RUN-001").json()["state"] == "EVIDENCE_READY"
    assert client.get("/api/patches/PATCH-001").json()["status"] == "applied"
    assert _matrix_statuses() == {"rerun_passed"}
    evidence = client.get("/api/runs/RUN-001/evidence")
    assert evidence.status_code == 200
    assert "Fixture evidence, no live model calls" in evidence.text


def test_post_resets_completed_fixture_run(monkeypatch, tmp_path):
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()
    client.post("/api/patches/PATCH-001/approve", json={"actor": "melinda.emerson", "note": "ready"})
    assert client.post("/api/runs/RUN-001/rerun").json()["state"] == "EVIDENCE_READY"

    _post_fixture()

    store = Store(db_path)
    assert store.get_run("RUN-001").state == "PATCH_PENDING"
    assert store.get_patch("PATCH-001").status == "pending"
    assert len(store.list_requirements("RUN-001")) == 3
    assert len(store.list_tests("RUN-001")) == 3
    assert len(store.list_failures("RUN-001")) == 3
    assert len(store.list_patches("RUN-001")) == 1


def test_evidence_after_completed_rerun(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()
    client.post("/api/patches/PATCH-001/approve", json={"actor": "melinda.emerson", "note": "ready"})
    client.post("/api/runs/RUN-001/rerun")

    html = client.get("/api/runs/RUN-001/evidence").text

    for expected in [
        "Release Assurance Evidence Pack",
        "Run provenance",
        "Summary",
        "Traceability matrix",
        "Failure evidence",
        "Proposed patch",
        "Decision record",
        "State transition audit trail",
        "Fixture evidence, no live model calls",
        "EVIDENCE_READY",
        "melinda.emerson",
        "PATCH-001",
        "FAIL-001",
        "PATCH_APPROVED",
        "RERUNNING",
    ]:
        assert expected in html


def test_evidence_after_rejection(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    _post_fixture()
    client.post("/api/patches/PATCH-001/reject", json={"actor": "melinda.emerson", "note": "not safe"})

    html = client.get("/api/runs/RUN-001/evidence").text

    assert "PATCH_REJECTED" in html
    assert "melinda.emerson" in html
    assert "No rerun was performed" in html


def test_repeated_identical_completed_fixture_runs_produce_identical_evidence(monkeypatch, tmp_path):
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    approval_request = {"actor": "melinda.emerson", "note": "Deterministic approval"}

    _post_fixture()
    client.post("/api/patches/PATCH-001/approve", json=approval_request)
    first_rerun = client.post("/api/runs/RUN-001/rerun")
    assert first_rerun.json()["state"] == "EVIDENCE_READY"
    first_html = client.get("/api/runs/RUN-001/evidence").text

    _post_fixture()
    client.post("/api/patches/PATCH-001/approve", json=approval_request)
    second_rerun = client.post("/api/runs/RUN-001/rerun")
    assert second_rerun.json()["state"] == "EVIDENCE_READY"
    second_html = client.get("/api/runs/RUN-001/evidence").text

    assert first_html == second_html

    store = Store(db_path)
    run = store.get_run("RUN-001")
    patch = store.get_patch("PATCH-001")
    assert run.created_at == config.FIXTURE_CLOCK_AT
    assert run.updated_at == config.FIXTURE_CLOCK_AT
    assert patch.approved_at == config.FIXTURE_CLOCK_AT
    assert patch.applied_at == config.FIXTURE_CLOCK_AT
    assert all(transition.at == config.FIXTURE_CLOCK_AT for transition in store.list_state_transitions("RUN-001"))
