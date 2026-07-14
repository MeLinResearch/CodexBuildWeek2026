from __future__ import annotations

from reconcile.validate import coerce_value, validate_record


def test_number_and_currency_coercion_for_number_and_integer_fields():
    assert coerce_value("$1,250.00", "number") == 1250.0
    assert coerce_value("$1,250.00", "integer") == 1250
    assert coerce_value(" 1_250 ", "number") == 1250.0
    assert coerce_value("bad", "number") is None


def test_integer_coercion_rejects_fractional_values_instead_of_truncating():
    assert coerce_value("1.9", "integer") is None
    assert coerce_value("2.0", "integer") == 2


def test_bad_email_fails_validation_after_coercion():
    schema = {"fields": {"email": {"type": "email", "required": True}}}
    record = {"email": coerce_value("not-an-email", "email")}
    assert validate_record(record, schema) == ["missing required field 'email'"]


def test_missing_required_field_fails_validation():
    schema = {"fields": {"name": {"type": "string", "required": True}}}
    assert validate_record({"name": None}, schema) == ["missing required field 'name'"]
    assert validate_record({"name": ""}, schema) == ["missing required field 'name'"]


def test_boolean_coercion_accepts_supported_true_and_false_values():
    for value in ["true", "yes", "y", "1", "t", "active", "TRUE", " Active "]:
        assert coerce_value(value, "boolean") is True
    for value in ["false", "no", "n", "0", "f", "inactive", "FALSE", " Inactive "]:
        assert coerce_value(value, "boolean") is False
    assert coerce_value("maybe", "boolean") is None


def test_date_validation_normalizes_valid_dates_and_rejects_invalid_dates():
    assert coerce_value("2024-01-15", "date") == "2024-01-15"
    assert coerce_value("01/15/2024", "date") == "2024-01-15"
    assert coerce_value("01-15-2024", "date") == "2024-01-15"
    assert coerce_value("15/01/2024", "date") == "2024-01-15"
    assert coerce_value("2024/01/15", "date") == "2024-01-15"
    assert coerce_value("Jan 15, 2024", "date") == "2024-01-15"
    assert coerce_value("January 15, 2024", "date") == "2024-01-15"
    assert coerce_value("Jan 15 2024", "date") == "2024-01-15"
    assert coerce_value("January 15 2024", "date") == "2024-01-15"
    assert coerce_value("2024/99/99", "date") is None

    schema = {"fields": {"start": {"type": "date", "required": True}}}
    assert validate_record({"start": None}, schema) == ["missing required field 'start'"]
    assert validate_record({"start": "2024-01-15"}, schema) == []


def test_enum_validation_accepts_allowed_value_and_rejects_disallowed_value():
    schema = {
        "fields": {
            "status": {
                "type": "string",
                "required": True,
                "enum": ["active", "inactive"],
            }
        }
    }
    assert validate_record({"status": "active"}, schema) == []
    assert validate_record({"status": "pending"}, schema) == [
        "field 'status' value 'pending' not in allowed set ['active', 'inactive']"
    ]
    assert validate_record({"status": 1}, schema) == [
        "field 'status' failed type 'string' (got 1)"
    ]
