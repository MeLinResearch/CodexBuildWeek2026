from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from reconcile.migration import MigrationResult, migrate_records


class LiveCheckError(RuntimeError):
    """Raised when the live migration checks cannot characterize the expected defects."""


@dataclass(frozen=True)
class LiveCheckFailure:
    record_id: str
    field: str
    expected: str
    actual: str
    severity: str
    record_hash: str


@dataclass(frozen=True)
class LiveCheckResult:
    migration_result: MigrationResult
    field_validation_failure: LiveCheckFailure
    balancing_failure: LiveCheckFailure
    exception_handling_failure: LiveCheckFailure

    @property
    def failures(self) -> tuple[LiveCheckFailure, LiveCheckFailure, LiveCheckFailure]:
        return (self.field_validation_failure, self.balancing_failure, self.exception_handling_failure)


def canonical_record_hash(record: Mapping[str, Any]) -> str:
    canonical = json.dumps(dict(record), sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def format_decimal(value: Decimal) -> str:
    return f"{value:.2f}"


def _detect_leading_zero_failure(
    source_records: Sequence[Mapping[str, str]], migrated_by_id: Mapping[str, Mapping[str, Any]]
) -> LiveCheckFailure:
    for record in source_records:
        account_id = record["account_id"]
        if not account_id.startswith("0"):
            continue
        migrated = migrated_by_id.get(record["record_id"])
        if migrated is None or migrated["account_id"] == account_id:
            continue
        return LiveCheckFailure(
            record_id=record["record_id"],
            field="account_id",
            expected=account_id,
            actual=str(migrated["account_id"]),
            severity="blocking",
            record_hash=canonical_record_hash(record),
        )
    raise LiveCheckError("leading-zero account identifier defect was not detected")


def _detect_branch_balance_failure(
    source_records: Sequence[Mapping[str, str]],
    migrated_records: Sequence[Mapping[str, Any]],
    branch_balances: Sequence[Any],
) -> LiveCheckFailure:
    source_by_id = {record["record_id"]: record for record in source_records}
    for balance in sorted(branch_balances, key=lambda item: item.branch):
        if balance.difference == Decimal("0.00"):
            continue
        credit_record = next(
            (
                record
                for record in migrated_records
                if record["branch"] == balance.branch and record["txn_code"] == "CREDIT"
            ),
            None,
        )
        if credit_record is None:
            continue
        record_id = credit_record["record_id"]
        source_record = source_by_id[record_id]
        expected = (
            f"Branch {balance.branch} debits {format_decimal(balance.debit_total)} "
            f"credits {format_decimal(balance.credit_total)} diff {format_decimal(balance.difference)}"
        )
        return LiveCheckFailure(
            record_id=record_id,
            field=f"branch_{balance.branch}_balance",
            expected=expected,
            actual=format_decimal(balance.difference),
            severity="blocking",
            record_hash=canonical_record_hash(source_record),
        )
    raise LiveCheckError("branch balance defect was not detected")


def _detect_invalid_date_failure(
    source_records: Sequence[Mapping[str, str]], migrated_by_id: Mapping[str, Mapping[str, Any]]
) -> LiveCheckFailure:
    for record in source_records:
        raw_date = record["effective_date"].strip()
        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            migrated = migrated_by_id.get(record["record_id"])
            if migrated is None:
                raise LiveCheckError("unparseable effective date defect was not detected") from None
            return LiveCheckFailure(
                record_id=record["record_id"],
                field="effective_date",
                expected="reject unparseable date",
                actual=str(migrated["effective_date"]),
                severity="blocking",
                record_hash=canonical_record_hash(record),
            )
    raise LiveCheckError("unparseable effective date defect was not detected")


def _validate_migrated_records(migrated_records: Sequence[Mapping[str, Any]], target_schema: Mapping[str, Any]) -> None:
    validator = Draft202012Validator(dict(target_schema))
    for record in migrated_records:
        errors = list(validator.iter_errors(dict(record)))
        if errors:
            raise LiveCheckError(f"migrated record {record.get('record_id')} failed target schema validation")


def run_live_checks(
    source_records: Sequence[Mapping[str, str]], target_schema: Mapping[str, Any]
) -> LiveCheckResult:
    migration_result = migrate_records(source_records)
    _validate_migrated_records(migration_result.migrated_records, target_schema)
    migrated_by_id = {record["record_id"]: record for record in migration_result.migrated_records}

    field_validation_failure = _detect_leading_zero_failure(source_records, migrated_by_id)
    balancing_failure = _detect_branch_balance_failure(
        source_records, migration_result.migrated_records, migration_result.branch_balances
    )
    exception_handling_failure = _detect_invalid_date_failure(source_records, migrated_by_id)

    return LiveCheckResult(
        migration_result=migration_result,
        field_validation_failure=field_validation_failure,
        balancing_failure=balancing_failure,
        exception_handling_failure=exception_handling_failure,
    )
