from __future__ import annotations

import pytest

from app.store.db import Store
from app.store.models import ArtifactRow, RequirementRow, RunRow, TestRow


def _store(tmp_path, clock=lambda: "2026-07-12T00:00:00Z"):
    s = Store(tmp_path / "ids.sqlite", clock=clock)
    s.init_schema()
    return s


def test_allocate_id_starts_at_one_by_default(tmp_path):
    s = _store(tmp_path)
    assert s.allocate_id("RUN") == "RUN-001"
    assert s.allocate_id("ART") == "ART-001"


def test_allocate_ids_returns_contiguous_block(tmp_path):
    s = _store(tmp_path)
    assert s.allocate_ids("REQ", 3, start=4) == ("REQ-004", "REQ-005", "REQ-006")


def test_allocate_id_skips_persisted_ids(tmp_path):
    s = _store(tmp_path)
    s.insert_run(RunRow("RUN-001", "CREATED", "fixture", "2026-07-12.1", "t0", "t0"))
    assert s.allocate_id("RUN") == "RUN-002"


def test_fixture_ids_remain_reserved_below_live_floor(tmp_path):
    s = _store(tmp_path)
    s.insert_run(RunRow("RUN-001", "CREATED", "fixture", "2026-07-12.1", "t0", "t0"))
    assert s.allocate_id("RUN", start=2) == "RUN-002"

    for artifact_id in ["ART-001", "ART-002", "ART-006", "ART-007", "ART-008", "ART-009"]:
        s.insert_artifact(
            ArtifactRow(
                artifact_id, "RUN-001", "input", "fixtures/x", "sha256:abc", "fixture", "fixture",
                "none", "not_required", "t0",
            )
        )
    assert s.allocate_id("ART", start=10) == "ART-010"


def test_live_allocation_advances_past_ids_already_used_within_floor(tmp_path):
    s = _store(tmp_path)
    s.insert_run(RunRow("RUN-002", "CREATED", "live", "2026-07-12.1", "t0", "t0"))
    assert s.allocate_id("RUN", start=2) == "RUN-003"


def test_new_store_instance_observes_persisted_ids_and_advances(tmp_path):
    db_path = tmp_path / "ids.sqlite"
    first = Store(db_path, clock=lambda: "2026-07-12T00:00:00Z")
    first.init_schema()
    first.insert_run(RunRow("RUN-001", "CREATED", "fixture", "2026-07-12.1", "t0", "t0"))

    second = Store(db_path, clock=lambda: "2026-07-12T00:00:00Z")
    assert second.allocate_id("RUN") == "RUN-002"


def test_injected_id_generator_still_used_by_create_run(tmp_path):
    calls = {"RUN": 0}

    def ids(prefix):
        calls[prefix] = calls.get(prefix, 0) + 1
        return f"{prefix}-{calls[prefix]:03d}"

    s = Store(tmp_path / "ids.sqlite", clock=lambda: "2026-07-12T00:00:00Z", id_generator=ids)
    s.init_schema()
    first = s.create_run("fixture", "2026-07-12.1")
    second = s.create_run("fixture", "2026-07-12.1")
    assert [first.run_id, second.run_id] == ["RUN-001", "RUN-002"]


def test_create_run_without_id_generator_uses_allocate_id(tmp_path):
    s = _store(tmp_path)
    first = s.create_run("fixture", "2026-07-12.1")
    second = s.create_run("fixture", "2026-07-12.1")
    assert [first.run_id, second.run_id] == ["RUN-001", "RUN-002"]


def test_default_store_does_not_create_fresh_sequential_generator(tmp_path):
    s = _store(tmp_path)
    assert s.id_generator is None


def test_allocate_id_rejects_unsupported_prefix(tmp_path):
    s = _store(tmp_path)
    with pytest.raises(ValueError):
        s.allocate_id("BOGUS")


def test_allocate_ids_rejects_nonpositive_count(tmp_path):
    s = _store(tmp_path)
    with pytest.raises(ValueError):
        s.allocate_ids("RUN", 0)
    with pytest.raises(ValueError):
        s.allocate_ids("RUN", -1)


def test_allocate_id_rejects_overflow_above_999(tmp_path):
    s = _store(tmp_path)
    with pytest.raises(ValueError):
        s.allocate_id("RUN", start=1000)


def test_allocate_ids_rejects_when_block_would_overflow(tmp_path):
    s = _store(tmp_path)
    with pytest.raises(ValueError):
        s.allocate_ids("RUN", 5, start=997)


def test_set_test_result_updates_status_and_output_ref(tmp_path):
    s = _store(tmp_path)
    s.insert_run(RunRow("RUN-001", "CREATED", "fixture", "2026-07-12.1", "t0", "t0"))
    s.insert_requirement(
        RequirementRow("REQ-001", "RUN-001", "text", "balancing_rule", None, {"schema_version": "2026-07-12.1"})
    )
    s.insert_test(TestRow("TEST-001", "RUN-001", "REQ-001", "n", "pending", None, {"schema_version": "2026-07-12.1"}))

    updated = s.set_test_result("TEST-001", "failed", "ART-010")

    assert updated.status == "failed"
    assert updated.output_ref == "ART-010"
    assert s.get_test("TEST-001") == updated


def test_set_test_result_rejects_invalid_status(tmp_path):
    s = _store(tmp_path)
    with pytest.raises(ValueError):
        s.set_test_result("TEST-001", "pending", None)


def test_set_test_result_raises_for_unknown_test(tmp_path):
    s = _store(tmp_path)
    with pytest.raises(LookupError):
        s.set_test_result("TEST-404", "passed", None)
