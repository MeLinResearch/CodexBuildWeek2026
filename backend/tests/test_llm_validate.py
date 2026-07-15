from __future__ import annotations

import copy
import json

import pytest

from app.config import FIXTURES_DIR
from app.llm.validate import LLMValidationError, load_schema, validate_control_manifest, validate_output


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


def test_unknown_schema_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_schema("missing.schema.json")


def test_validate_control_manifest_wrapper_passes():
    payload = _control_manifest_fixture()

    assert validate_control_manifest(payload) is payload
