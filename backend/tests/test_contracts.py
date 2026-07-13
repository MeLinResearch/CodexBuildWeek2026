import json
from pathlib import Path

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
