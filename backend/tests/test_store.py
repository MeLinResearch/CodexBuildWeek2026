import sqlite3

import pytest

from app import config
from app.config import make_sequential_id_generator
from app.store.db import Store
from app.store.models import (
    ArtifactRow,
    FailureRow,
    PatchRow,
    RequirementRow,
    RunRow,
    TestRow as StoreTestRow,
)


def store(tmp_path, clock=lambda: "2026-07-12T00:00:00Z"):
    s = Store(tmp_path / "test.sqlite", clock=clock)
    s.init_schema()
    return s


def run_row(run_id="RUN-001", state="CREATED"):
    return RunRow(run_id, state, "fixture", "2026-07-12.1", "t0", "t0")


def provenance(run_id="RUN-001"):
    return {"schema_version": "2026-07-12.1", "run_id": run_id, "ok": True}


def requirement_row(requirement_id="REQ-001", run_id="RUN-001"):
    return RequirementRow(requirement_id, run_id, "Must balance", "balancing_rule", None, provenance(run_id))


def make_test_row(test_id="TEST-001", run_id="RUN-001", requirement_id="REQ-001", status="pending"):
    return StoreTestRow(test_id, run_id, requirement_id, "test balance", status, None, provenance(run_id))


def failure_row(failure_id="FAIL-001", run_id="RUN-001", requirement_id="REQ-001", test_id="TEST-001"):
    return FailureRow(
        failure_id,
        run_id,
        requirement_id,
        test_id,
        "REC-001",
        "amount",
        "100",
        "99",
        "blocking",
        "sha256:abc",
        provenance(run_id),
    )


def patch_row(patch_id="PATCH-001", run_id="RUN-001", failure_ids=None):
    return PatchRow(patch_id, run_id, failure_ids or ["FAIL-001"], "diff --git", "pending", None, None, None, provenance(run_id))


def artifact_row(artifact_id="ART-001", run_id="RUN-001", producer="fixture"):
    return ArtifactRow(
        artifact_id,
        run_id,
        "input",
        "fixtures/input.txt",
        "sha256:abc",
        producer,
        "fixture",
        "none",
        "not_required",
        "t0",
    )


def test_schema_init_idempotent(tmp_path):
    s = Store(tmp_path / "test.sqlite")
    s.init_schema()
    s.init_schema()


def test_fk_enforcement_works(tmp_path):
    s = store(tmp_path)
    s.insert_run(run_row())
    with pytest.raises(sqlite3.IntegrityError):
        s.insert_test(make_test_row(requirement_id="REQ-404"))


def test_enum_check_constraints_reject_invalid_values(tmp_path):
    s = store(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        s.insert_run(run_row(state="BOGUS"))
    s.insert_run(run_row())
    s.insert_requirement(requirement_row())
    with pytest.raises(sqlite3.IntegrityError):
        s.insert_test(make_test_row(status="bogus"))
    with pytest.raises(sqlite3.IntegrityError):
        s.insert_artifact(artifact_row(producer="bogus"))


def test_provenance_json_constraints_reject_invalid_raw_json(tmp_path):
    s = store(tmp_path)
    s.insert_run(run_row())
    with s.connect() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO requirements (requirement_id, run_id, text, rule_type, tolerance, provenance)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("REQ-001", "RUN-001", "Must balance", "balancing_rule", None, "{bad json"),
        )


def test_python_side_provenance_must_be_dict(tmp_path):
    s = store(tmp_path)
    s.insert_run(run_row())
    for bad_provenance in ("{bad json", ["bad"], None):
        row = RequirementRow("REQ-001", "RUN-001", "Must balance", "balancing_rule", None, bad_provenance)
        with pytest.raises(TypeError):
            s.insert_requirement(row)


def test_python_side_provenance_keys_must_be_strings(tmp_path):
    s = store(tmp_path)
    s.insert_run(run_row())
    row = RequirementRow("REQ-001", "RUN-001", "Must balance", "balancing_rule", None, {1: "bad"})
    with pytest.raises(TypeError):
        s.insert_requirement(row)


def test_python_side_patch_failure_ids_must_be_list_of_strings(tmp_path):
    s = store(tmp_path)
    s.insert_run(run_row())
    for bad_failure_ids in ("FAIL-001", [1, 2], None):
        row = PatchRow("PATCH-001", "RUN-001", bad_failure_ids, "diff --git", "pending", None, None, None, provenance())
        with pytest.raises(TypeError):
            s.insert_patch(row)


def test_store_default_db_path_uses_config(monkeypatch, tmp_path):
    db_path = tmp_path / "default.sqlite"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    s = Store()
    s.init_schema()
    assert db_path.exists()


def test_id_generator_respects_requested_prefix():
    gen = make_sequential_id_generator()
    assert gen("RUN") == "RUN-001"
    assert gen("ART") == "ART-001"
    assert gen("RUN") == "RUN-002"

    gen = make_sequential_id_generator("RUN")
    assert gen("") == "RUN-001"
    assert gen("ART") == "ART-001"


def test_artifact_run_id_may_be_none(tmp_path):
    s = store(tmp_path)
    row = artifact_row(run_id=None)
    s.insert_artifact(row)
    assert s.get_artifact("ART-001").run_id is None
    assert s.list_artifacts() == [row]


def test_state_transition_fk_guard(tmp_path):
    s = store(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        s.insert_state_transition("RUN-404", None, "INGESTED", "test_actor")


def test_json_serialization_roundtrip(tmp_path):
    s = store(tmp_path)
    s.insert_run(run_row())
    row = requirement_row()
    s.insert_requirement(row)
    assert s.get_requirement("REQ-001").provenance == row.provenance


def test_patch_failure_ids_json_roundtrip(tmp_path):
    s = store(tmp_path)
    s.insert_run(run_row())
    row = patch_row(failure_ids=["FAIL-001", "FAIL-002"])
    s.insert_patch(row)
    assert s.get_patch("PATCH-001").failure_ids == ["FAIL-001", "FAIL-002"]


def test_order_by_behavior(tmp_path):
    s = store(tmp_path)
    s.insert_run(run_row("RUN-002"))
    s.insert_run(run_row("RUN-001"))
    s.insert_requirement(requirement_row("REQ-002", "RUN-001"))
    s.insert_requirement(requirement_row("REQ-001", "RUN-001"))
    s.insert_test(make_test_row("TEST-002"))
    s.insert_test(make_test_row("TEST-001"))
    s.insert_failure(failure_row("FAIL-002"))
    s.insert_failure(failure_row("FAIL-001"))
    s.insert_patch(patch_row("PATCH-002"))
    s.insert_patch(patch_row("PATCH-001"))
    s.insert_artifact(artifact_row("ART-002"))
    s.insert_artifact(artifact_row("ART-001"))
    s.insert_state_transition("RUN-001", "CREATED", "INGESTED", "actor")
    s.insert_state_transition("RUN-001", "INGESTED", "TRIAGED", "actor")

    assert [r.run_id for r in s.list_runs()] == ["RUN-001", "RUN-002"]
    assert [r.requirement_id for r in s.list_requirements("RUN-001")] == ["REQ-001", "REQ-002"]
    assert [r.test_id for r in s.list_tests("RUN-001")] == ["TEST-001", "TEST-002"]
    assert [r.failure_id for r in s.list_failures("RUN-001")] == ["FAIL-001", "FAIL-002"]
    assert [r.patch_id for r in s.list_patches("RUN-001")] == ["PATCH-001", "PATCH-002"]
    assert [r.artifact_id for r in s.list_artifacts("RUN-001")] == ["ART-001", "ART-002"]
    assert [r.id for r in s.list_state_transitions("RUN-001")] == [1, 2]


def test_fixed_clock_and_injected_id_generator(tmp_path):
    calls = {"RUN": 0}

    def ids(prefix):
        calls[prefix] = calls.get(prefix, 0) + 1
        return f"{prefix}-{calls[prefix]:03d}"

    s = Store(tmp_path / "test.sqlite", clock=lambda: "2026-07-12T00:00:00Z", id_generator=ids)
    s.init_schema()
    first = s.create_run("fixture", "2026-07-12.1")
    second = s.create_run("fixture", "2026-07-12.1")
    assert [first.run_id, second.run_id] == ["RUN-001", "RUN-002"]
    assert first.created_at == first.updated_at == "2026-07-12T00:00:00Z"
    assert second.created_at == second.updated_at == "2026-07-12T00:00:00Z"


def test_insert_state_transition_atomic_behavior(tmp_path):
    s = Store(tmp_path / "test.sqlite", clock=lambda: "2026-07-12T00:00:00Z")
    s.init_schema()
    s.create_run("fixture", "2026-07-12.1", state="CREATED", run_id="RUN-001")
    transition = s.insert_state_transition("RUN-001", "CREATED", "INGESTED", "test_actor")
    assert transition.to_state == "INGESTED"
    assert transition.at == "2026-07-12T00:00:00Z"
    assert s.list_state_transitions("RUN-001") == [transition]
    run = s.get_run("RUN-001")
    assert run.state == "INGESTED"
    assert run.updated_at == transition.at


def test_delete_cascade_smoke_test(tmp_path):
    s = store(tmp_path)
    s.insert_run(run_row())
    s.insert_requirement(requirement_row())
    s.insert_test(make_test_row())
    s.insert_failure(failure_row())
    s.insert_patch(patch_row())
    with s.connect() as conn:
        conn.execute("DELETE FROM runs WHERE run_id = ?", ("RUN-001",))
    assert s.list_requirements("RUN-001") == []
    assert s.list_tests("RUN-001") == []
    assert s.list_failures("RUN-001") == []
    assert s.list_patches("RUN-001") == []
