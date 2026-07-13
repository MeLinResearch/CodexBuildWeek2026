import re

from app.pipeline.mock_pipeline import run_fixture_pipeline
from app.store.db import Store

FIXED_CLOCK = "2026-07-12T00:00:00Z"


def store(tmp_path):
    return Store(tmp_path / "pipeline.sqlite", clock=lambda: FIXED_CLOCK)


def populated_store(tmp_path):
    s = store(tmp_path)
    run_fixture_pipeline(s)
    return s


def test_creates_run(tmp_path):
    run = run_fixture_pipeline(store(tmp_path))

    assert run.run_id == "RUN-001"
    assert run.mode == "fixture"
    assert run.schema_version == "2026-07-12.1"
    assert run.state == "PATCH_PENDING"


def test_persists_exact_state_transitions(tmp_path):
    s = populated_store(tmp_path)

    transitions = s.list_state_transitions("RUN-001")

    assert [(row.from_state, row.to_state) for row in transitions] == [
        ("CREATED", "INGESTED"),
        ("INGESTED", "MANIFEST_READY"),
        ("MANIFEST_READY", "TESTS_GENERATED"),
        ("TESTS_GENERATED", "EXECUTED"),
        ("EXECUTED", "TRIAGED"),
        ("TRIAGED", "PATCH_PENDING"),
    ]
    assert [row.actor for row in transitions] == ["mock_pipeline"] * 6
    assert [row.at for row in transitions] == [FIXED_CLOCK] * 6


def test_persists_exact_requirements(tmp_path):
    requirements = populated_store(tmp_path).list_requirements("RUN-001")

    assert [row.requirement_id for row in requirements] == ["REQ-001", "REQ-002", "REQ-003"]
    assert [(row.requirement_id, row.text, row.rule_type) for row in requirements] == [
        ("REQ-001", "preserve account identifiers verbatim", "field_validation"),
        ("REQ-002", "debits equal credits by branch", "balancing_rule"),
        ("REQ-003", "no silent value substitution", "exception_handling"),
    ]
    assert [row.tolerance for row in requirements] == [None, None, None]


def test_persists_exact_tests(tmp_path):
    tests = populated_store(tmp_path).list_tests("RUN-001")

    assert [(row.test_id, row.requirement_id, row.name, row.status, row.output_ref) for row in tests] == [
        ("TEST-001", "REQ-001", "preserve account identifiers verbatim", "failed", "ART-006"),
        ("TEST-002", "REQ-002", "debits equal credits by branch", "failed", "ART-007"),
        ("TEST-003", "REQ-003", "no silent value substitution", "failed", "ART-008"),
    ]


def test_persists_exact_failures(tmp_path):
    s = populated_store(tmp_path)
    failures = s.list_failures("RUN-001")
    test_ids = {row.test_id for row in s.list_tests("RUN-001")}
    requirement_ids = {row.requirement_id for row in s.list_requirements("RUN-001")}

    assert [(row.failure_id, row.requirement_id, row.test_id, row.field, row.severity) for row in failures] == [
        ("FAIL-001", "REQ-001", "TEST-001", "account_id", "blocking"),
        ("FAIL-002", "REQ-002", "TEST-002", "branch_101_balance", "blocking"),
        ("FAIL-003", "REQ-003", "TEST-003", "effective_date", "blocking"),
    ]
    assert [row.run_id for row in failures] == ["RUN-001"] * 3
    assert all(row.test_id in test_ids for row in failures)
    assert all(row.requirement_id in requirement_ids for row in failures)


def test_persists_exact_patch(tmp_path):
    patches = populated_store(tmp_path).list_patches("RUN-001")

    assert len(patches) == 1
    patch = patches[0]
    assert patch.patch_id == "PATCH-001"
    assert patch.status == "pending"
    assert patch.failure_ids == ["FAIL-001", "FAIL-002", "FAIL-003"]
    assert patch.approved_by is None
    assert patch.approved_at is None
    assert patch.applied_at is None
    assert patch.provenance["client"] == "FixtureCodexClient"


def test_persists_exact_artifacts(tmp_path):
    artifacts = populated_store(tmp_path).list_artifacts("RUN-001")
    artifacts_by_id = {row.artifact_id: row for row in artifacts}

    assert list(artifacts_by_id) == ["ART-001", "ART-002", "ART-006", "ART-007", "ART-008", "ART-009"]
    assert [row.run_id for row in artifacts] == ["RUN-001"] * 6
    assert [row.mode for row in artifacts] == ["fixture"] * 6
    assert artifacts_by_id["ART-001"].producer == "deterministic"
    assert artifacts_by_id["ART-001"].client == "none"
    assert artifacts_by_id["ART-001"].validation_status == "not_required"
    assert artifacts_by_id["ART-009"].kind == "patch_diff"
    assert artifacts_by_id["ART-009"].client == "FixtureCodexClient"
    assert all(re.fullmatch(r"[0-9a-f]{64}", row.sha256) for row in artifacts)


def test_idempotency(tmp_path):
    s = store(tmp_path)

    first = run_fixture_pipeline(s)
    second = run_fixture_pipeline(s)

    assert first.run_id == second.run_id == "RUN-001"
    assert first.state == second.state == "PATCH_PENDING"
    assert len(s.list_requirements("RUN-001")) == 3
    assert len(s.list_tests("RUN-001")) == 3
    assert len(s.list_failures("RUN-001")) == 3
    assert len(s.list_patches("RUN-001")) == 1
    assert len(s.list_artifacts("RUN-001")) == 6
    transitions = s.list_state_transitions("RUN-001")
    transition_pairs = [(row.from_state, row.to_state) for row in transitions]
    assert len(transitions) == 6
    assert len(set(transition_pairs)) == 6


def test_ignores_live_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-that-must-not-be-used")

    s = store(tmp_path)
    run = run_fixture_pipeline(s)

    assert run.state == "PATCH_PENDING"
    assert all(row.mode == "fixture" for row in s.list_artifacts("RUN-001"))
