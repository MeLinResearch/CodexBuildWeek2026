from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH_FIXTURE = ROOT / "fixtures/api/patch_PATCH-001.fixture.json"
FRONTEND_PATCH_FIXTURE = ROOT / "frontend/src/mocks/patch_PATCH-001.fixture.json"
MIGRATION_SOURCE = ROOT / "reconcile/migration.py"
SOURCE_DATA = ROOT / "fixtures/source_data/accounts.csv"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def _load_patched_module(path: Path):
    module_name = "release_assurance_patched_migration"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    return module


def test_fixture_patch_frontend_copy_matches_and_targets_only_migration():
    backend_proposal = _load_json(PATCH_FIXTURE)
    frontend_proposal = _load_json(FRONTEND_PATCH_FIXTURE)

    assert backend_proposal == frontend_proposal

    diff = backend_proposal["diff"]
    assert isinstance(diff, str)
    assert diff.count("diff --git ") == 1
    assert diff.startswith(
        "diff --git a/reconcile/migration.py b/reconcile/migration.py\n"
    )
    assert "-    return str(int(raw.strip()))" in diff
    assert "+    return raw.strip()" in diff
    assert '-        return "1900-01-01"' in diff
    assert "-        return amount" in diff
    assert "+        return -amount" in diff


def test_fixture_patch_applies_and_repairs_all_planted_defects(tmp_path: Path):
    proposal = _load_json(PATCH_FIXTURE)
    workspace = tmp_path / "workspace"
    destination = workspace / "reconcile/migration.py"
    destination.parent.mkdir(parents=True)
    destination.write_text(
        MIGRATION_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )

    patch_path = workspace / "PATCH-001.diff"
    patch_path.write_text(
        str(proposal["diff"]),
        encoding="utf-8",
        newline="\n",
    )

    check_result = subprocess.run(
        ["git", "apply", "--check", patch_path.name],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    assert check_result.returncode == 0, check_result.stderr

    apply_result = subprocess.run(
        ["git", "apply", patch_path.name],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    assert apply_result.returncode == 0, apply_result.stderr

    patched = _load_patched_module(destination)
    with SOURCE_DATA.open(newline="") as handle:
        records = list(csv.DictReader(handle))

    result = patched.migrate_records(records)

    assert result.migrated_records == (
        {
            "record_id": "TXN-000001",
            "account_id": "00012345",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": Decimal("1250.00"),
            "txn_code": "DEBIT",
            "signed_amount": Decimal("1250.00"),
        },
        {
            "record_id": "TXN-000002",
            "account_id": "00067890",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": Decimal("1200.00"),
            "txn_code": "CREDIT",
            "signed_amount": Decimal("-1200.00"),
        },
        {
            "record_id": "TXN-000004",
            "account_id": "00033333",
            "branch": "101",
            "effective_date": "2026-07-01",
            "amount": Decimal("50.00"),
            "txn_code": "CREDIT_ADJUSTMENT",
            "signed_amount": Decimal("-50.00"),
        },
    )
    assert result.rejected_records == (
        {
            "record_id": "TXN-000003",
            "field": "effective_date",
            "reason": "unparseable date",
        },
    )
    assert result.branch_balances == (
        patched.BranchBalance(
            branch="101",
            debit_total=Decimal("1250.00"),
            credit_total=Decimal("1250.00"),
            difference=Decimal("0.00"),
        ),
    )
