from __future__ import annotations

import copy
import json

import pytest
from jsonschema import ValidationError

from app.config import FIXTURES_DIR
from app.llm.validate import validate_control_manifest


def _control_manifest_fixture():
    with (FIXTURES_DIR / "model_outputs" / "control_manifest.fixture.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def test_validate_control_manifest_accepts_frozen_fixture():
    payload = _control_manifest_fixture()

    assert validate_control_manifest(payload) is payload


def test_validate_control_manifest_rejects_model_shaped_output_with_extra_fields():
    payload = copy.deepcopy(_control_manifest_fixture())
    payload["unexpected_model_field"] = "not in the frozen contract"

    with pytest.raises(ValidationError):
        validate_control_manifest(payload)


def test_validate_control_manifest_resolves_nested_provenance_contract_refs():
    payload = copy.deepcopy(_control_manifest_fixture())
    del payload["requirements"][0]["provenance"]["client"]

    with pytest.raises(ValidationError):
        validate_control_manifest(payload)
