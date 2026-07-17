from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from app.pipeline.live_checks import LiveCheckError, canonical_record_hash, run_live_checks

ROOT = Path(__file__).resolve().parents[2]
SOURCE_CSV = ROOT / "fixtures/source_data/accounts.csv"
TARGET_SCHEMA = ROOT / "fixtures/schemas/target_schema.json"


def _records():
    with SOURCE_CSV.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _schema():
    return json.loads(TARGET_SCHEMA.read_text())


def test_detects_exact_three_canonical_defects():
    result = run_live_checks(_records(), _schema())

    field = result.field_validation_failure
    assert field.record_id == "TXN-000001"
    assert field.field == "account_id"
    assert field.expected == "00012345"
    assert field.actual == "12345"
    assert field.severity == "blocking"

    balance = result.balancing_failure
    assert balance.record_id == "TXN-000002"
    assert balance.field == "branch_101_balance"
    assert balance.expected == "Branch 101 debits 1250.00 credits 1200.00 diff 50.00"
    assert balance.actual == "50.00"
    assert balance.severity == "blocking"

    date = result.exception_handling_failure
    assert date.record_id == "TXN-000003"
    assert date.field == "effective_date"
    assert date.expected == "reject unparseable date"
    assert date.actual == "1900-01-01"
    assert date.severity == "blocking"


def test_record_hashes_are_real_sha256_of_source_record():
    records = _records()
    result = run_live_checks(records, _schema())
    source_by_id = {r["record_id"]: r for r in records}

    for failure in result.failures:
        expected_hash = canonical_record_hash(source_by_id[failure.record_id])
        assert failure.record_hash == expected_hash
        assert failure.record_hash.startswith("sha256:")
        assert len(failure.record_hash) == len("sha256:") + 64


def test_failure_ordering_is_stable_field_balance_date():
    result = run_live_checks(_records(), _schema())
    assert [f.field for f in result.failures] == ["account_id", "branch_101_balance", "effective_date"]
    assert [f.record_id for f in result.failures] == ["TXN-000001", "TXN-000002", "TXN-000003"]


def test_migrated_records_are_validated_against_target_schema():
    result = run_live_checks(_records(), _schema())
    assert len(result.migration_result.migrated_records) == 4
    assert result.migration_result.rejected_records == ()


def test_schema_validation_failure_raises():
    impossible_schema = {
        "type": "object",
        "required": ["account_id", "branch", "effective_date", "amount", "txn_code", "not_a_real_field"],
    }
    with pytest.raises(LiveCheckError):
        run_live_checks(_records(), impossible_schema)


def test_fails_if_leading_zero_defect_is_absent():
    records = [
        {
            "record_id": "TXN-1",
            "account_id": "12345",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": "10.00",
            "txn_code": "DEBIT",
        },
    ]
    with pytest.raises(LiveCheckError):
        run_live_checks(records, _schema())


def test_fails_if_branch_balance_defect_is_absent():
    records = [
        {
            "record_id": "TXN-1",
            "account_id": "0100",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": "100.00",
            "txn_code": "DEBIT",
        },
        {
            "record_id": "TXN-2",
            "account_id": "0200",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": "100.00",
            "txn_code": "CREDIT",
        },
    ]
    with pytest.raises(LiveCheckError):
        run_live_checks(records, _schema())


def test_fails_if_invalid_date_defect_is_absent():
    records = [
        {
            "record_id": "TXN-1",
            "account_id": "0100",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": "150.00",
            "txn_code": "DEBIT",
        },
        {
            "record_id": "TXN-2",
            "account_id": "0200",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": "100.00",
            "txn_code": "CREDIT",
        },
    ]
    with pytest.raises(LiveCheckError):
        run_live_checks(records, _schema())
