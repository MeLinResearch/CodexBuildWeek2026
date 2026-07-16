"""Deliberately flawed deterministic migration target for the Release Assurance live repair demonstration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

_CENT = Decimal("0.01")
_ZERO = Decimal("0.00")


@dataclass(frozen=True)
class BranchBalance:
    branch: str
    debit_total: Decimal
    credit_total: Decimal
    difference: Decimal


@dataclass(frozen=True)
class MigrationResult:
    migrated_records: tuple[dict[str, object], ...]
    rejected_records: tuple[dict[str, str], ...]
    branch_balances: tuple[BranchBalance, ...]


def _normalize_account_id(raw: str) -> str:
    return str(int(raw.strip()))


def _parse_effective_date(raw: str) -> str:
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return "1900-01-01"


def _parse_amount(raw: str) -> Decimal:
    return Decimal(raw.strip()).quantize(_CENT)


def _signed_amount(txn_code: str, amount: Decimal) -> Decimal:
    if txn_code == "DEBIT":
        return amount
    if txn_code == "CREDIT":
        return -amount
    if txn_code == "CREDIT_ADJUSTMENT":
        return amount
    raise ValueError(f"unsupported transaction code: {txn_code}")


def _summarize_branches(
    migrated_records: Sequence[Mapping[str, object]],
) -> tuple[BranchBalance, ...]:
    branches = sorted({str(record["branch"]) for record in migrated_records})
    balances: list[BranchBalance] = []
    for branch in branches:
        branch_records = [
            record for record in migrated_records if record["branch"] == branch
        ]
        debit_total = sum(
            (
                record["amount"]
                for record in branch_records
                if record["txn_code"] == "DEBIT"
            ),
            _ZERO,
        ).quantize(_CENT)
        credit_total = sum(
            (
                record["amount"]
                for record in branch_records
                if record["signed_amount"] < _ZERO
            ),
            _ZERO,
        ).quantize(_CENT)
        balances.append(
            BranchBalance(
                branch=branch,
                debit_total=debit_total,
                credit_total=credit_total,
                difference=abs(debit_total - credit_total).quantize(_CENT),
            )
        )
    return tuple(balances)


def migrate_records(
    records: Sequence[Mapping[str, str]],
) -> MigrationResult:
    migrated_records: list[dict[str, object]] = []
    rejected_records: list[dict[str, str]] = []
    for record in records:
        record_id = record["record_id"].strip()
        try:
            effective_date = _parse_effective_date(record["effective_date"])
        except ValueError:
            rejected_records.append(
                {
                    "record_id": record_id,
                    "field": "effective_date",
                    "reason": "unparseable date",
                }
            )
            continue
        amount = _parse_amount(record["amount"])
        txn_code = record["txn_code"].strip().upper()
        migrated_records.append(
            {
                "record_id": record_id,
                "account_id": _normalize_account_id(record["account_id"]),
                "branch": record["branch"].strip(),
                "effective_date": effective_date,
                "amount": amount,
                "txn_code": txn_code,
                "signed_amount": _signed_amount(txn_code, amount),
            }
        )
    return MigrationResult(
        migrated_records=tuple(migrated_records),
        rejected_records=tuple(rejected_records),
        branch_balances=_summarize_branches(migrated_records),
    )
