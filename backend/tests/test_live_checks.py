import hashlib
import json
from app import config
from app.pipeline.live_checks import execute_live_checks


def test_canonical_migration_defects_are_detected():
    schema = json.loads((config.FIXTURES_DIR / "schemas/target_schema.json").read_text())
    result = execute_live_checks(config.FIXTURES_DIR / "source_data/accounts.csv", schema)
    assert [(x["field"], x["actual"]) for x in result["failures"]] == [
        ("account_id", "12345"), ("branch_101_balance", "50.00"),
        ("effective_date", "1900-01-01")]
    source = result["records"][0]
    expected = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert result["failures"][0]["record_hash"] == "sha256:" + expected
