from __future__ import annotations

import urllib.request

import pytest

from app.config import RUN_ID_FIXTURE
from app.llm import FixtureLLMClient, LLMClient, LLMValidationError


def _extract(client: LLMClient):
    return client.extract_requirements(
        implementation_doc="fixture implementation doc",
        run_id=RUN_ID_FIXTURE,
        source_artifact_ids=["ART-001"],
    )


def test_fixture_llm_client_returns_valid_control_manifest():
    payload = _extract(FixtureLLMClient())

    assert payload["run_id"] == "RUN-001"
    assert [requirement["requirement_id"] for requirement in payload["requirements"]] == ["REQ-001", "REQ-002", "REQ-003"]
    assert payload["provenance"]["client"] == "FixtureLLMClient"
    assert payload["provenance"]["producer"] == "fixture"
    assert payload["provenance"]["mode"] == "fixture"
    assert payload["provenance"]["validation_status"] == "validated"


def test_fixture_llm_client_returns_fresh_objects():
    client = FixtureLLMClient()

    first = _extract(client)
    second = _extract(client)
    first["requirements"].append(first["requirements"][0])

    assert len(second["requirements"]) == 3


def test_fixture_llm_client_ignores_openai_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")

    payload = _extract(FixtureLLMClient())

    assert payload["provenance"]["producer"] == "fixture"


def test_fixture_llm_client_does_not_call_network(monkeypatch):
    def fail_urlopen(*args, **kwargs):
        raise AssertionError("FixtureLLMClient must not call the network")

    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)

    payload = _extract(FixtureLLMClient())

    assert payload["run_id"] == "RUN-001"


def test_fixture_llm_client_validates_loaded_fixture(tmp_path):
    invalid_fixture = tmp_path / "invalid_control_manifest.json"
    invalid_fixture.write_text('{"run_id": "RUN-001", "requirements": []}', encoding="utf-8")
    client = FixtureLLMClient(fixture_path=invalid_fixture)

    with pytest.raises(LLMValidationError):
        _extract(client)
