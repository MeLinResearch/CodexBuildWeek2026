from __future__ import annotations

import copy
import json

import pytest

from app.config import FIXTURES_DIR
from app.llm.validate import LLMValidationError, bundle_schema_for_model, load_schema, validate_control_manifest, validate_output


def _control_manifest_fixture():
    with (FIXTURES_DIR / "model_outputs" / "control_manifest.fixture.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def test_validate_control_manifest_fixture_passes():
    payload = _control_manifest_fixture()

    assert validate_output("control_manifest.schema.json", payload) is payload


def test_validate_rejects_extra_fields():
    payload = copy.deepcopy(_control_manifest_fixture())
    payload["unexpected_model_field"] = "not in the frozen contract"

    with pytest.raises(LLMValidationError) as exc_info:
        validate_output("control_manifest.schema.json", payload)

    assert "control_manifest.schema.json" in str(exc_info.value)


def test_validate_rejects_invalid_provenance_client():
    payload = copy.deepcopy(_control_manifest_fixture())
    payload["provenance"]["client"] = "BogusClient"

    with pytest.raises(LLMValidationError) as exc_info:
        validate_output("control_manifest.schema.json", payload)

    assert "provenance" in exc_info.value.path
    assert "client" in exc_info.value.path


def test_validate_rejects_invalid_created_at_format():
    payload = copy.deepcopy(_control_manifest_fixture())
    payload["provenance"]["created_at"] = "not-a-date"

    with pytest.raises(LLMValidationError) as exc_info:
        validate_output("control_manifest.schema.json", payload)

    assert "provenance" in exc_info.value.path
    assert "created_at" in exc_info.value.path
    assert "control_manifest.schema.json" in str(exc_info.value)


def test_unknown_schema_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_schema("missing.schema.json")


def test_validate_control_manifest_wrapper_passes():
    payload = _control_manifest_fixture()

    assert validate_control_manifest(payload) is payload


def test_bundle_schema_is_fresh_internal_and_does_not_affect_contract():
    original = load_schema("control_manifest.schema.json")
    first = bundle_schema_for_model("control_manifest.schema.json")
    second = bundle_schema_for_model("control_manifest.schema.json")

    assert first == second and first is not second
    assert "provenance" in first["$defs"]
    assert ".schema.json" not in json.dumps(first)
    assert "$schema" not in first and "$id" not in first
    requirement_properties = first["properties"]["requirements"]["items"]["properties"]
    provenance_properties = first["$defs"]["provenance"]["properties"]
    assert requirement_properties["rule_type"]["type"] == "string"
    assert provenance_properties["schema_version"]["type"] == "string"
    for name in ("client", "mode", "producer", "validation_status"):
        assert provenance_properties[name]["type"] == "string"
    assert load_schema("control_manifest.schema.json") == original
    assert validate_output("control_manifest.schema.json", _control_manifest_fixture())
