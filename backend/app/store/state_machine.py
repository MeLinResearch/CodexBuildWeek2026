from __future__ import annotations

from app.store.db import Store
from app.store.models import RunState, StateTransitionRow

_TERMINAL_STATES: frozenset[RunState] = frozenset({"DONE", "FAILED"})

_BASE_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    "CREATED": frozenset({"INGESTED"}),
    "INGESTED": frozenset({"MANIFEST_READY"}),
    "MANIFEST_READY": frozenset({"TESTS_GENERATED"}),
    "TESTS_GENERATED": frozenset({"EXECUTED"}),
    "EXECUTED": frozenset({"TRIAGED"}),
    "TRIAGED": frozenset({"EVIDENCE_READY", "PATCH_PENDING"}),
    "PATCH_PENDING": frozenset({"PATCH_APPROVED", "PATCH_REJECTED"}),
    "PATCH_REJECTED": frozenset({"TRIAGED"}),
    "PATCH_APPROVED": frozenset({"RERUNNING"}),
    "RERUNNING": frozenset({"EVIDENCE_READY", "TRIAGED"}),
    "EVIDENCE_READY": frozenset({"DONE"}),
    "DONE": frozenset(),
    "FAILED": frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when a requested run state transition is not legal."""


class RunNotFoundError(LookupError):
    """Raised when a run cannot be found for a requested transition."""


def allowed_transitions(from_state: RunState) -> set[RunState]:
    """Return the legal outgoing states for a run state."""
    if from_state in _TERMINAL_STATES:
        return set()

    transitions = set(_BASE_TRANSITIONS[from_state])
    transitions.add("FAILED")
    return transitions


def can_transition(from_state: RunState, to_state: RunState) -> bool:
    """Return whether a transition is legal in the frozen run state graph."""
    return to_state in allowed_transitions(from_state)


def transition_run(
    store: Store, run_id: str, to_state: RunState, actor: str
) -> StateTransitionRow:
    """Validate, persist, and return a run state transition."""
    run = store.get_run(run_id)
    if run is None:
        raise RunNotFoundError(f"Run not found: {run_id}")

    from_state = run.state
    if not can_transition(from_state, to_state):
        raise InvalidTransitionError(f"Cannot transition run {run_id} from {from_state} to {to_state}")

    return store.insert_state_transition(run_id, from_state, to_state, actor)
