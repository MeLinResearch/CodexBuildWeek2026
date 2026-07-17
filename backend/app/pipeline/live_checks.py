"""Deterministic execution and defect detection for live runs."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from reconcile.migration import migrate_records


class LiveChecksError(RuntimeError):
    pass


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), ".2f")


def record_hash(record: dict[str, str]) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def execute_live_checks(source_path: Path, target_schema: dict[str, Any]) -> dict[str, Any]:
    with source_path.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    result = migrate_records(records)
    migrated = list(result.migrated_records)
    for row in migrated:
        # Decimal is a valid numeric migration value, but jsonschema only recognizes
        # standard Python numbers by default.
        candidate = {k: float(v) if isinstance(v, Decimal) else v for k, v in row.items()}
        Draft202012Validator(target_schema).validate(candidate)
    by_id = {str(row["record_id"]): row for row in migrated}
    failures: list[dict[str, str]] = []

    leading = next((r for r in records if r["account_id"].startswith("0") and
                    str(by_id.get(r["record_id"], {}).get("account_id")) != r["account_id"]), None)
    if leading:
        failures.append({"record_id": leading["record_id"], "field": "account_id",
                         "expected": leading["account_id"],
                         "actual": str(by_id[leading["record_id"]]["account_id"]),
                         "severity": "blocking", "record_hash": record_hash(leading)})

    balance = next((b for b in sorted(result.branch_balances, key=lambda b: b.branch)
                    if b.difference != Decimal("0")), None)
    if balance:
        source = next((r for r in records if r["branch"] == balance.branch and
                       r["txn_code"].strip().upper() == "CREDIT"), None)
        if source:
            failures.append({"record_id": source["record_id"],
                             "field": f"branch_{balance.branch}_balance",
                             "expected": f"Branch {balance.branch} debits {_money(balance.debit_total)} credits {_money(balance.credit_total)} diff {_money(balance.difference)}",
                             "actual": _money(balance.difference), "severity": "blocking",
                             "record_hash": record_hash(source)})

    invalid = next((r for r in records if _invalid_date(r["effective_date"])), None)
    if invalid and invalid["record_id"] in by_id:
        substituted = str(by_id[invalid["record_id"]]["effective_date"])
        if substituted != invalid["effective_date"]:
            failures.append({"record_id": invalid["record_id"], "field": "effective_date",
                             "expected": "reject unparseable date", "actual": substituted,
                             "severity": "blocking", "record_hash": record_hash(invalid)})
    if len(failures) != 3:
        raise LiveChecksError("all three planted migration defects were not detected")
    return {"records": records, "result": result, "failures": failures}


def _invalid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return False
    except ValueError:
        return True

