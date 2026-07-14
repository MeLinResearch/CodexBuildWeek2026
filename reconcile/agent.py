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
        return len(self.clean_records) / total if total else 0.0


def _apply_and_validate(
    records: list[dict[str, Any]],
    mapping: dict[str, Any],
    target_schema: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    clean: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for rec in records:
        transformed: dict[str, Any] = {}
        for target_name, rule in mapping.items():
            source_name = rule.get("source")
            target_type = rule.get("type", "string")
            raw = rec.get(source_name) if source_name else None
            transformed[target_name] = coerce_value(raw, target_type)

        errors = validate_record(transformed, target_schema)
        if errors:
            failed.append(
                {
                    "_record": rec,
                    "_errors": errors,
                    "_partial": transformed,
                }
            )
        else:
            clean.append(transformed)

    return clean, failed


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
    failures_for_feedback: list[dict[str, Any]] | None = None
    log: list[str] = []

    last_mapping: dict[str, Any] = {}
    clean: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for round_num in range(1, max_rounds + 1):
        mapping = propose(
            sample=sample,
            target_schema=target_schema,
            previous_mapping=previous_mapping,
            failures=failures_for_feedback,
        )
        last_mapping = mapping
        log.append(
            f"round {round_num}: proposed mapping for {len(mapping)} target fields"
        )

        clean, failed = _apply_and_validate(records, mapping, target_schema)
        log.append(
            f"round {round_num}: {len(clean)} ok, {len(failed)} failed "
            f"({len(clean) / max(len(records), 1):.0%})"
        )

        if not failed:
            return ReconcileResult(mapping, clean, failed, round_num, log)

        previous_mapping = mapping
        failures_for_feedback = [
            failure["_record"] for failure in failed[:sample_size]
        ]

    return ReconcileResult(last_mapping, clean, failed, max_rounds, log)


def to_json(result: ReconcileResult) -> str:
    return json.dumps(
        {
            "mapping": result.mapping,
            "success_rate": round(result.success_rate, 3),
            "rounds_used": result.rounds_used,
            "clean_count": len(result.clean_records),
            "failed_count": len(result.failed_records),
            "log": result.log,
        },
        indent=2,
    )
