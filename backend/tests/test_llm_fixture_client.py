from __future__ import annotations

import pytest
from jsonschema import ValidationError

from app.config import RUN_ID_FIXTURE
from app.llm import FixtureLLMClient, LLMClient


def test_fixture_llm_client_loads_validated_control_manifest():
    client: LLMClient = FixtureLLMClient()

    payload = client.extract_requirements(
        implementation_doc="fixture implementation doc",
        run_id=RUN_ID_FIXTURE,
        source_artifact_ids=["ART-001"],
    )

    assert payload["run_id"] == "RUN-001"
    assert [requirement["requirement_id"] for requirement in payload["requirements"]] == ["REQ-001", "REQ-002", "REQ-003"]
    assert payload["provenance"]["client"] == "FixtureLLMClient"
    assert payload["provenance"]["producer"] == "fixture"
    assert payload["provenance"]["mode"] == "fixture"
    assert payload["provenance"]["validation_status"] == "validated"


def test_fixture_llm_client_returns_fresh_payload_copy():
    client = FixtureLLMClient()

    first = client.extract_requirements(implementation_doc="doc", run_id=RUN_ID_FIXTURE, source_artifact_ids=["ART-001"])
    first["requirements"].append(first["requirements"][0])
    second = client.extract_requirements(implementation_doc="doc", run_id=RUN_ID_FIXTURE, source_artifact_ids=["ART-001"])

    assert len(second["requirements"]) == 3


def test_fixture_llm_client_validates_loaded_fixture(tmp_path):
    invalid_fixture = tmp_path / "invalid_control_manifest.json"
    invalid_fixture.write_text('{"run_id": "RUN-001", "requirements": []}', encoding="utf-8")
    client = FixtureLLMClient(fixture_path=invalid_fixture)

    with pytest.raises(ValidationError):
        client.extract_requirements(implementation_doc="doc", run_id=RUN_ID_FIXTURE, source_artifact_ids=["ART-001"])
