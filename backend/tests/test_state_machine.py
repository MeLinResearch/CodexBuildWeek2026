import pytest

from app.store.db import Store
from app.store.state_machine import (
    InvalidTransitionError,
    RunNotFoundError,
    allowed_transitions,
    transition_run,
)

FIXED_CLOCK = "2026-07-12T00:00:00Z"
SCHEMA_VERSION = "2026-07-12.1"
ACTOR = "state_machine_test"


def store(tmp_path):
    s = Store(tmp_path / "test.sqlite", clock=lambda: FIXED_CLOCK)
    s.init_schema()
    return s


def create_run(s, run_id="RUN-001", state="CREATED"):
    return s.create_run("fixture", SCHEMA_VERSION, state=state, run_id=run_id)


def walk_path(s, run_id, path, actor=ACTOR):
    transitions = []
    for to_state in path[1:]:
        transitions.append(transition_run(s, run_id, to_state, actor))
    return transitions


def assert_persisted_path(s, run_id, path, actor=ACTOR):
    transitions = s.list_state_transitions(run_id)
    assert [(row.from_state, row.to_state) for row in transitions] == list(zip(path, path[1:]))
    assert [row.actor for row in transitions] == [actor] * (len(path) - 1)
    assert [row.at for row in transitions] == [FIXED_CLOCK] * (len(path) - 1)


def test_every_legal_transition_in_representative_path_succeeds_and_persists(tmp_path):
    s = store(tmp_path)
    run = create_run(s)
    path = [
        "CREATED",
        "INGESTED",
        "MANIFEST_READY",
        "TESTS_GENERATED",
        "EXECUTED",
        "TRIAGED",
        "PATCH_PENDING",
        "PATCH_APPROVED",
        "RERUNNING",
        "EVIDENCE_READY",
        "DONE",
    ]

    walk_path(s, run.run_id, path)

    assert s.get_run(run.run_id).state == "DONE"
    assert_persisted_path(s, run.run_id, path)


def test_clean_run_legal_path(tmp_path):
    s = store(tmp_path)
    run = create_run(s)
    path = [
        "CREATED",
        "INGESTED",
        "MANIFEST_READY",
        "TESTS_GENERATED",
        "EXECUTED",
        "TRIAGED",
        "EVIDENCE_READY",
        "DONE",
    ]

    walk_path(s, run.run_id, path)

    assert s.get_run(run.run_id).state == "DONE"
    assert_persisted_path(s, run.run_id, path)


def test_rejected_patch_legal_path(tmp_path):
    s = store(tmp_path)
    run = create_run(s, state="TRIAGED")
    path = ["TRIAGED", "PATCH_PENDING", "PATCH_REJECTED", "TRIAGED"]

    walk_path(s, run.run_id, path)

    assert s.get_run(run.run_id).state == "TRIAGED"
    assert_persisted_path(s, run.run_id, path)


def test_rerun_still_failing_legal_path(tmp_path):
    s = store(tmp_path)
    run = create_run(s, state="PATCH_APPROVED")
    path = ["PATCH_APPROVED", "RERUNNING", "TRIAGED"]

    walk_path(s, run.run_id, path)

    assert s.get_run(run.run_id).state == "TRIAGED"
    assert_persisted_path(s, run.run_id, path)


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        ("CREATED", "DONE"),
        ("TRIAGED", "DONE"),
        ("PATCH_PENDING", "RERUNNING"),
        ("EVIDENCE_READY", "TRIAGED"),
        ("DONE", "FAILED"),
        ("FAILED", "TRIAGED"),
    ],
)
def test_illegal_transitions_reject(tmp_path, from_state, to_state):
    s = store(tmp_path)
    run = create_run(s, state=from_state)

    with pytest.raises(InvalidTransitionError):
        transition_run(s, run.run_id, to_state, ACTOR)

    assert s.get_run(run.run_id).state == from_state
    assert s.list_state_transitions(run.run_id) == []


@pytest.mark.parametrize(
    "from_state",
    [
        "CREATED",
        "INGESTED",
        "MANIFEST_READY",
        "TESTS_GENERATED",
        "EXECUTED",
        "TRIAGED",
        "PATCH_PENDING",
        "PATCH_APPROVED",
        "PATCH_REJECTED",
        "RERUNNING",
        "EVIDENCE_READY",
    ],
)
def test_failed_allowed_from_every_non_terminal_state(tmp_path, from_state):
    s = store(tmp_path)
    run = create_run(s, state=from_state)

    transition = transition_run(s, run.run_id, "FAILED", ACTOR)

    assert transition.from_state == from_state
    assert transition.to_state == "FAILED"
    assert s.get_run(run.run_id).state == "FAILED"


def test_terminal_states_have_no_allowed_outgoing_transitions():
    assert allowed_transitions("DONE") == set()
    assert allowed_transitions("FAILED") == set()


def test_missing_run_raises_run_not_found(tmp_path):
    s = store(tmp_path)

    with pytest.raises(RunNotFoundError):
        transition_run(s, "RUN-404", "INGESTED", ACTOR)


def test_actor_persisted(tmp_path):
    s = store(tmp_path)
    run = create_run(s)

    transition = transition_run(s, run.run_id, "INGESTED", ACTOR)

    assert transition.actor == ACTOR
    assert s.list_state_transitions(run.run_id)[0].actor == ACTOR
