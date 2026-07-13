from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

RunState = Literal[
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
    "DONE",
    "FAILED",
]
RunMode = Literal["live", "fixture"]
RuleType = Literal[
    "field_validation",
    "balancing_rule",
    "exception_handling",
    "mapping_rule",
    "tolerance_rule",
]
TestStatus = Literal["pending", "passed", "failed", "skipped"]
FailureSeverity = Literal["blocking", "warning", "info"]
PatchStatus = Literal["pending", "approved", "rejected", "applied", "apply_failed"]
ArtifactKind = Literal[
    "input",
    "raw_model_output",
    "validated_model_output",
    "test_output",
    "patch_diff",
    "evidence_html",
    "evidence_pdf",
    "log",
]
ArtifactProducer = Literal["gpt-5.6", "codex", "deterministic", "fixture"]
ValidationStatus = Literal["not_required", "quarantined", "validated", "rejected"]


@dataclass(frozen=True)
class RunRow:
    run_id: str
    state: RunState
    mode: RunMode
    schema_version: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class StateTransitionRow:
    id: int
    run_id: str
    from_state: RunState | None
    to_state: RunState
    actor: str
    at: str


@dataclass(frozen=True)
class RequirementRow:
    requirement_id: str
    run_id: str
    text: str
    rule_type: RuleType
    tolerance: str | None
    provenance: dict[str, Any]


@dataclass(frozen=True)
class TestRow:
    test_id: str
    run_id: str
    requirement_id: str
    name: str
    status: TestStatus
    output_ref: str | None
    provenance: dict[str, Any]


@dataclass(frozen=True)
class FailureRow:
    failure_id: str
    run_id: str
    requirement_id: str
    test_id: str
    record_id: str
    field: str | None
    expected: str
    actual: str | None
    severity: FailureSeverity
    record_hash: str | None
    provenance: dict[str, Any]


@dataclass(frozen=True)
class PatchRow:
    patch_id: str
    run_id: str
    failure_ids: list[str]
    diff: str
    status: PatchStatus
    approved_by: str | None
    approved_at: str | None
    applied_at: str | None
    provenance: dict[str, Any]


@dataclass(frozen=True)
class ArtifactRow:
    artifact_id: str
    run_id: str | None
    kind: ArtifactKind
    path: str
    sha256: str
    producer: ArtifactProducer
    mode: RunMode
    client: str
    validation_status: ValidationStatus
    created_at: str
