from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Callable

from .heuristic import propose_mapping
from .validate import coerce_value, validate_record


@dataclass
class ReconcileResult:
    mapping: dict[str, Any]
    clean_records: list[dict[str, Any]]
    failed_records: list[dict[str, Any]]
    rounds_used: int
    log: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = len(self.clean_records) + len(self.failed_records)
        if total == 0:
            return 1.0
        return len(self.clean_records) / total


def _transform_record(record: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    transformed: dict[str, Any] = {}
    for target_field, rule in mapping.items():
        source = rule.get("source")
        target_type = rule.get("type", "string")
        raw = record.get(source) if source is not None else None
        transformed[target_field] = coerce_value(raw, target_type)
    return transformed


def reconcile(
    records: list[dict[str, Any]],
    target_schema: dict[str, Any],
    *,
    max_rounds: int = 3,
    sample_size: int = 8,
    propose: Callable[..., dict[str, Any]] = propose_mapping,
) -> ReconcileResult:
    sample = records[:sample_size]
    previous_mapping: dict[str, Any] | None = None
    failures: list[dict[str, Any]] | None = None
    log: list[str] = []

    final_mapping: dict[str, Any] = {}
    clean_records: list[dict[str, Any]] = []
    failed_records: list[dict[str, Any]] = []

    for round_number in range(1, max_rounds + 1):
        mapping = propose(
            sample=sample,
            target_schema=target_schema,
            previous_mapping=previous_mapping,
            failures=failures,
        )
        final_mapping = mapping
        clean_records = []
        failed_records = []

        for record in records:
            transformed = _transform_record(record, mapping)
            errors = validate_record(transformed, target_schema)
            if errors:
                failed_records.append(
                    {
                        "_record": record.copy(),
                        "_errors": errors,
                        "_partial": transformed,
                    }
                )
            else:
                clean_records.append(transformed)

        log.append(
            f"round {round_number}: {len(clean_records)} clean, {len(failed_records)} failed"
        )

        if not failed_records:
            return ReconcileResult(mapping, clean_records, failed_records, round_number, log)

        previous_mapping = mapping
        failures = [failure["_record"] for failure in failed_records]

    return ReconcileResult(final_mapping, clean_records, failed_records, max_rounds, log)


def to_json(result: ReconcileResult) -> str:
    return json.dumps(
        {
            "mapping": result.mapping,
            "clean_records": result.clean_records,
            "failed_records": result.failed_records,
            "rounds_used": result.rounds_used,
            "success_rate": result.success_rate,
            "log": result.log,
        },
        indent=2,
    )
