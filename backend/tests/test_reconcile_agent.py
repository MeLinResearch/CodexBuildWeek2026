from __future__ import annotations

from copy import deepcopy

from reconcile import reconcile

TARGET_SCHEMA = {
    "fields": {
        "full_name": {"type": "string", "required": True},
        "email": {"type": "email", "required": True},
        "amount": {"type": "number", "required": False},
        "signup_date": {"type": "date", "required": True},
        "active": {"type": "boolean", "required": False},
    }
}

GOOD_MAPPING = {
    "full_name": {"source": "name", "type": "string"},
    "email": {"source": "email", "type": "email"},
    "amount": {"source": "amount", "type": "number"},
    "signup_date": {"source": "joined", "type": "date"},
    "active": {"source": "status", "type": "boolean"},
}


class StaticProposer:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def __call__(self, *, sample, target_schema, previous_mapping, failures):
        self.calls.append(
            {
                "sample": sample,
                "target_schema": target_schema,
                "previous_mapping": previous_mapping,
                "failures": failures,
            }
        )
        return self.mapping


class SequenceProposer:
    def __init__(self, mappings):
        self.mappings = list(mappings)
        self.calls = []

    def __call__(self, *, sample, target_schema, previous_mapping, failures):
        self.calls.append(
            {
                "sample": sample,
                "target_schema": target_schema,
                "previous_mapping": previous_mapping,
                "failures": failures,
            }
        )
        return self.mappings[len(self.calls) - 1]


def test_clean_records_are_transformed_successfully():
    records = [
        {
            "name": " Jane Doe ",
            "email": "JANE@EXAMPLE.COM",
            "amount": "$1,250.00",
            "joined": "01/15/2024",
            "status": "active",
        }
    ]
    proposer = StaticProposer(GOOD_MAPPING)

    result = reconcile(records, TARGET_SCHEMA, propose=proposer)

    assert result.clean_records == [
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "amount": 1250.0,
            "signup_date": "2024-01-15",
            "active": True,
        }
    ]
    assert result.failed_records == []
    assert result.rounds_used == 1
    assert result.success_rate == 1.0
    assert proposer.calls[0]["sample"] == records
    assert proposer.calls[0]["target_schema"] == TARGET_SCHEMA
    assert proposer.calls[0]["previous_mapping"] is None
    assert proposer.calls[0]["failures"] is None


def test_invalid_records_are_separated_with_auditable_failure_information():
    records = [
        {
            "name": "Wei Chen",
            "email": "not-an-email",
            "amount": "450.50",
            "joined": "03/22/2024",
            "status": "active",
        }
    ]
    proposer = StaticProposer(GOOD_MAPPING)

    result = reconcile(records, TARGET_SCHEMA, max_rounds=1, propose=proposer)

    assert result.clean_records == []
    assert result.failed_records == [
        {
            "_record": records[0],
            "_errors": ["missing required field 'email'"],
            "_partial": {
                "full_name": "Wei Chen",
                "email": None,
                "amount": 450.5,
                "signup_date": "2024-03-22",
                "active": True,
            },
        }
    ]
    assert result.success_rate == 0.0


def test_missing_required_field_does_not_silently_pass_or_get_invented():
    records = [{"name": "No Date", "email": "person@example.com", "amount": "5", "status": "yes"}]
    proposer = StaticProposer(GOOD_MAPPING)

    result = reconcile(records, TARGET_SCHEMA, max_rounds=1, propose=proposer)

    assert result.failed_records[0]["_errors"] == ["missing required field 'signup_date'"]
    assert result.failed_records[0]["_partial"]["signup_date"] is None


def test_input_records_are_not_mutated_in_place():
    records = [
        {
            "name": "Jane Doe",
            "email": "JANE@EXAMPLE.COM",
            "amount": "1,250",
            "joined": "2024-01-15",
            "status": "active",
        }
    ]
    original = deepcopy(records)

    reconcile(records, TARGET_SCHEMA, propose=StaticProposer(GOOD_MAPPING))

    assert records == original


def test_retry_uses_failure_feedback_and_accepts_corrected_mapping():
    records = [
        {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "amount": "1,250",
            "joined": "2024-01-15",
            "status": "active",
        }
    ]
    bad_mapping = {
        **GOOD_MAPPING,
        "signup_date": {"source": "missing", "type": "date"},
    }
    proposer = SequenceProposer([bad_mapping, GOOD_MAPPING])

    result = reconcile(records, TARGET_SCHEMA, max_rounds=2, propose=proposer)

    assert result.clean_records == [
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "amount": 1250.0,
            "signup_date": "2024-01-15",
            "active": True,
        }
    ]
    assert result.failed_records == []
    assert result.rounds_used == 2
    assert proposer.calls[0]["previous_mapping"] is None
    assert proposer.calls[0]["failures"] is None
    assert proposer.calls[1]["previous_mapping"] == bad_mapping
    assert proposer.calls[1]["failures"] == [records[0]]
