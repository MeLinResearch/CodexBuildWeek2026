from __future__ import annotations

import csv
from copy import deepcopy
import json
from pathlib import Path

from reconcile import reconcile, to_json


def test_reconcile_fixture_is_expected_deterministic_and_live_free(monkeypatch):
    fixture_root = Path("reconcile/fixtures")
    with (fixture_root / "messy_records.csv").open(newline="") as handle:
        records = list(csv.DictReader(handle))
    with (fixture_root / "target_schema.json").open() as handle:
        schema = json.load(handle)
    original = deepcopy(records)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")

    first_result = reconcile(records, schema, max_rounds=1)
    second_result = reconcile(records, schema, max_rounds=1)

    assert records == original
    assert first_result.mapping == second_result.mapping
    assert first_result.clean_records == second_result.clean_records
    assert first_result.failed_records == second_result.failed_records
    assert first_result.rounds_used == second_result.rounds_used
    assert first_result.log == second_result.log
    assert to_json(first_result).encode("utf-8") == to_json(second_result).encode("utf-8")
    assert first_result.mapping == {
        "full_name": {"source": "Customer Name", "type": "string"},
        "email": {"source": "E-Mail", "type": "email"},
        "amount": {"source": "Total", "type": "number"},
        "signup_date": {"source": "Created", "type": "date"},
        "active": {"source": "Status", "type": "boolean"},
    }
    assert first_result.clean_records == [
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "amount": 1250.0,
            "signup_date": "2024-01-15",
            "active": True,
        },
        {
            "full_name": "Bob Smith",
            "email": "bob@example.com",
            "amount": 980.0,
            "signup_date": "2024-02-03",
            "active": True,
        },
        {
            "full_name": "Maria Garcia",
            "email": "maria@example.com",
            "amount": 2300.0,
            "signup_date": "2024-03-09",
            "active": False,
        },
        {
            "full_name": "Aisha Khan",
            "email": "aisha@example.com",
            "amount": 1100.0,
            "signup_date": "2024-04-01",
            "active": True,
        },
    ]
    assert len(first_result.failed_records) == 2
    assert first_result.failed_records[0]["_record"]["Customer Name"] == "Wei Chen"
    assert first_result.failed_records[1]["_record"]["Customer Name"] == "Tom Brown"
    assert first_result.failed_records[0]["_errors"] == ["missing required field 'email'"]
    assert first_result.failed_records[1]["_errors"] == ["missing required field 'signup_date'"]

    combined_source = "\n".join(
        path.read_text().lower() for path in Path("reconcile").glob("*.py")
    )
    assert "anthropic" not in combined_source
    assert "openai" not in combined_source
