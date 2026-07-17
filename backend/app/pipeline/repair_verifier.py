from __future__ import annotations

import csv
import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location("verified_migration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load patched migration")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify(module_path: Path, source_path: Path) -> dict[str, object]:
    module = _load_module(module_path)
    with source_path.open(newline="", encoding="utf-8") as handle:
        result = module.migrate_records(list(csv.DictReader(handle)))
    migrated = list(result.migrated_records)
    rejected = list(result.rejected_records)
    balances = list(result.branch_balances)
    if [row["account_id"] for row in migrated] != ["00012345", "00067890", "00033333"]:
        raise RuntimeError("account identifiers were not preserved")
    if rejected != [{"record_id": "TXN-000003", "field": "effective_date", "reason": "unparseable date"}]:
        raise RuntimeError("invalid date was not rejected")
    if len(balances) != 1 or balances[0].branch != "101" or balances[0].debit_total != Decimal("1250.00") or balances[0].credit_total != Decimal("1250.00") or balances[0].difference != Decimal("0.00"):
        raise RuntimeError("branch balance was not repaired")
    return {"checks": {"account_identifiers": "passed", "invalid_dates": "passed", "branch_balance": "passed"},
            "migrated_records": len(migrated), "rejected_records": len(rejected)}


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))
