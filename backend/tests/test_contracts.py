import json
from pathlib import Path

from test_fixtures import (
    test_all_json_valid as _verify_all_json_valid,
    test_fixture_contracts as _verify_fixture_contracts,
    test_frontend_mocks_match_backend_fixtures as _verify_frontend_mocks,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"

def test_contracts_are_draft_2020_12_with_ids():
    for path in sorted(CONTRACTS.glob("*.schema.json")):
        schema = json.loads(path.read_text())
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"]

def test_known_enum_values():
    run_status = json.loads((CONTRACTS / "run_status.schema.json").read_text())
    assert "PATCH_PENDING" in run_status["properties"]["state"]["enum"]
    row = json.loads((CONTRACTS / "traceability_row.schema.json").read_text())
    assert row["properties"]["row_status"]["enum"] == ["pending", "passed", "failed", "patch_pending", "patch_approved", "rerun_passed"]


def test_frozen_schema_version_matches_provenance_and_valid_fixtures():
    version = (CONTRACTS / "VERSION").read_text(encoding="utf-8").strip()
    assert version == "2026-07-12.1"

    provenance = json.loads((CONTRACTS / "provenance.schema.json").read_text(encoding="utf-8"))
    assert provenance["properties"]["schema_version"]["const"] == version

    _verify_all_json_valid()
    _verify_fixture_contracts()
    _verify_frontend_mocks()
