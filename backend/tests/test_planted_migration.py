from __future__ import annotations

import csv
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from reconcile.migration import BranchBalance, migrate_records

FIXTURE_PATH = Path("fixtures/source_data/accounts.csv")
EXPECTED_SOURCE_RECORDS = [
    {
        "record_id": "TXN-000001",
        "account_id": "00012345",
        "branch": "101",
        "effective_date": "2026-07-01",
        "amount": "1250.00",
        "txn_code": "DEBIT",
    },
    {
        "record_id": "TXN-000002",
        "account_id": "00067890",
        "branch": "101",
        "effective_date": "2026-07-01",
        "amount": "1200.00",
        "txn_code": "CREDIT",
    },
    {
        "record_id": "TXN-000003",
        "account_id": "00022222",
        "branch": "102",
        "effective_date": "not-a-date",
        "amount": "0.00",
        "txn_code": "DEBIT",
    },
    {
        "record_id": "TXN-000004",
        "account_id": "00033333",
        "branch": "101",
        "effective_date": "2026-07-01",
        "amount": "50.00",
        "txn_code": "CREDIT_ADJUSTMENT",
    },
]


def _load_records() -> list[dict[str, str]]:
    with FIXTURE_PATH.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_source_fixture_contains_exact_planted_records():
    assert _load_records() == EXPECTED_SOURCE_RECORDS


def test_migration_is_non_mutating_and_deterministic():
    records = _load_records()
    original = deepcopy(records)
    first_result = migrate_records(records)
    second_result = migrate_records(deepcopy(original))
    assert records == original
    assert first_result == second_result


def test_migrated_records_characterize_planted_defects():
    result = migrate_records(_load_records())
    assert result.migrated_records == (
        {
            "record_id": "TXN-000001",
            "account_id": "12345",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": Decimal("1250.00"),
            "txn_code": "DEBIT",
            "signed_amount": Decimal("1250.00"),
        },
        {
            "record_id": "TXN-000002",
            "account_id": "67890",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": Decimal("1200.00"),
            "txn_code": "CREDIT",
            "signed_amount": Decimal("-1200.00"),
        },
        {
            "record_id": "TXN-000003",
            "account_id": "22222",
            "branch": "102",
            "effective_date": "1900-01-01",
            "amount": Decimal("0.00"),
            "txn_code": "DEBIT",
            "signed_amount": Decimal("0.00"),
        },
        {
            "record_id": "TXN-000004",
            "account_id": "33333",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": Decimal("50.00"),
            "txn_code": "CREDIT_ADJUSTMENT",
            "signed_amount": Decimal("50.00"),
        },
    )
    assert result.migrated_records[0]["account_id"] == "12345"
    assert result.migrated_records[2]["effective_date"] == "1900-01-01"
    assert result.migrated_records[3]["signed_amount"] == Decimal("50.00")
    assert result.rejected_records == ()


def test_branch_balances_characterize_omitted_credit_adjustment():
    result = migrate_records(_load_records())
    assert result.branch_balances == (
        BranchBalance(
            branch="101",
            debit_total=Decimal("1250.00"),
            credit_total=Decimal("1200.00"),
            difference=Decimal("50.00"),
        ),
        BranchBalance(
            branch="102",
            debit_total=Decimal("0.00"),
            credit_total=Decimal("0.00"),
            difference=Decimal("0.00"),
        ),
    )
    assert tuple(balance.branch for balance in result.branch_balances) == ("101", "102")
