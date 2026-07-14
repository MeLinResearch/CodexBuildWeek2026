from __future__ import annotations

from copy import deepcopy

from reconcile import reconcile

TARGET_SCHEMA = {
    "fields": {
        "full_name": {"type": "string", "required": True},
        "email": {"type": "email", "required": True},
        "amount": {"type": "number", "required": False},
        "active": {"type": "boolean", "required": False},
    }
}

GOOD_MAPPING = {
    "full_name": {"source": "Customer Name", "type": "string"},
    "email": {"source": "E-Mail", "type": "email"},
    "amount": {"source": "Total", "type": "number"},
    "active": {"source": "Status", "type": "boolean"},
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
            "Customer Name": " Jane Doe ",
            "E-Mail": "JANE@EXAMPLE.COM",
            "Total": "$1,250.00",
            "Status": "active",
        }
    ]
    proposer = StaticProposer(GOOD_MAPPING)

    result = reconcile(records, TARGET_SCHEMA, propose=proposer)

    assert result.mapping == GOOD_MAPPING
    assert result.clean_records == [
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "amount": 1250.0,
            "active": True,
        }
    ]
    assert result.failed_records == []
    assert result.rounds_used == 1
    assert result.success_rate == 1.0
    assert result.log == [
        "round 1: proposed mapping for 4 target fields",
        "round 1: 1 ok, 0 failed (100%)",
    ]
    assert proposer.calls == [
        {
            "sample": records,
            "target_schema": TARGET_SCHEMA,
            "previous_mapping": None,
            "failures": None,
        }
    ]


def test_invalid_records_are_separated_with_auditable_failure_information():
    records = [
        {
            "Customer Name": "Wei Chen",
            "E-Mail": "not-an-email",
            "Total": "450.50",
            "Status": "active",
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
                "active": True,
            },
        }
    ]
    assert result.success_rate == 0.0
    assert result.log == [
        "round 1: proposed mapping for 4 target fields",
        "round 1: 0 ok, 1 failed (0%)",
    ]


def test_missing_required_field_does_not_silently_pass_or_get_invented():
    records = [{"E-Mail": "person@example.com", "Total": "5", "Status": "yes"}]
    proposer = StaticProposer(GOOD_MAPPING)

    result = reconcile(records, TARGET_SCHEMA, max_rounds=1, propose=proposer)

    assert result.failed_records == [
        {
            "_record": records[0],
            "_errors": ["missing required field 'full_name'"],
            "_partial": {
                "full_name": None,
                "email": "person@example.com",
                "amount": 5.0,
                "active": True,
            },
        }
    ]


def test_input_records_are_not_mutated_in_place():
    records = [
        {
            "Customer Name": "Jane Doe",
            "E-Mail": "JANE@EXAMPLE.COM",
            "Total": "1,250",
            "Status": "active",
        }
    ]
    original = deepcopy(records)

    reconcile(records, TARGET_SCHEMA, propose=StaticProposer(GOOD_MAPPING))

    assert records == original


def test_retry_uses_failure_feedback_and_accepts_corrected_mapping():
    records = [
        {
            "Customer Name": "Jane Doe",
            "E-Mail": "jane@example.com",
            "Total": "1,250",
            "Status": "active",
        }
    ]
    bad_mapping = {
        **GOOD_MAPPING,
        "email": {"source": "Missing Email", "type": "email"},
    }
    proposer = SequenceProposer([bad_mapping, GOOD_MAPPING])

    result = reconcile(records, TARGET_SCHEMA, max_rounds=2, propose=proposer)

    assert result.clean_records == [
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "amount": 1250.0,
            "active": True,
        }
    ]
    assert result.failed_records == []
    assert result.rounds_used == 2
    assert result.log == [
        "round 1: proposed mapping for 4 target fields",
        "round 1: 0 ok, 1 failed (0%)",
        "round 2: proposed mapping for 4 target fields",
        "round 2: 1 ok, 0 failed (100%)",
    ]
    assert proposer.calls[0]["previous_mapping"] is None
    assert proposer.calls[0]["failures"] is None
    assert proposer.calls[1]["previous_mapping"] == bad_mapping
    assert proposer.calls[1]["failures"] == [records[0]]
