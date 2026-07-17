import json
from types import SimpleNamespace

import pytest

from app.llm.live_client import LiveLLMClient, LiveLLMConfigurationError, LiveLLMResponseError


class Responses:
    def __init__(self, output): self.output, self.kwargs = output, None
    def create(self, **kwargs): self.kwargs = kwargs; return SimpleNamespace(output_text=self.output)


def manifest():
    provenance = {"run_id": "RUN-001", "schema_version": "2026-07-12.1", "created_at": "2026-07-12T00:00:00Z",
                  "source_artifact_ids": ["ART-001"], "producer": "gpt-5.6", "mode": "live",
                  "client": "LiveLLMClient", "validation_status": "validated"}
    return {"run_id": "RUN-001", "requirements": [{"requirement_id": "REQ-001", "text": "do thing",
            "rule_type": "field_validation", "provenance": provenance.copy()}], "provenance": provenance}


def client(tmp_path, output):
    responses = Responses(output)
    return LiveLLMClient(SimpleNamespace(responses=responses), clock=lambda: "2026-07-12T00:00:00Z",
                         quarantine_root=tmp_path, model_name="gpt-5.6"), responses


def test_valid_call_arguments_and_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr("app.llm.live_client.config.SCHEMA_VERSION", "2026-07-12.1")
    live, responses = client(tmp_path, json.dumps(manifest()))
    assert live.extract_requirements(implementation_doc="doc", run_id="RUN-001", source_artifact_ids=["ART-001"])["run_id"] == "RUN-001"
    assert responses.kwargs["model"] == "gpt-5.6"
    assert responses.kwargs["tools"] == [] and responses.kwargs["store"] is False
    assert responses.kwargs["text"]["format"]["strict"] is True
    assert "$defs" in responses.kwargs["text"]["format"]["schema"]
    requirement_schema = responses.kwargs["text"]["format"]["schema"]["properties"]["requirements"]["items"]
    assert set(requirement_schema["required"]) == set(requirement_schema["properties"])
    assert requirement_schema["properties"]["tolerance"]["type"] == ["string", "null"]
    context = json.loads(responses.kwargs["input"])
    assert context["implementation_doc"] == "doc" and context["provenance"]["client"] == "LiveLLMClient"


@pytest.mark.parametrize("output", ["not json", json.dumps({"run_id": "RUN-001"})])
def test_invalid_output_is_quarantined(tmp_path, monkeypatch, output):
    monkeypatch.setattr("app.llm.live_client.config.SCHEMA_VERSION", "2026-07-12.1")
    live, _ = client(tmp_path, output)
    with pytest.raises(LiveLLMResponseError):
        live.extract_requirements(implementation_doc="doc", run_id="RUN-001", source_artifact_ids=["ART-001"])
    assert (tmp_path / "llm/RUN-001/control_manifest.raw.json").read_text() == output


def test_wrong_provenance_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("app.llm.live_client.config.SCHEMA_VERSION", "2026-07-12.1")
    payload = manifest(); payload["provenance"]["created_at"] = "2026-07-13T00:00:00Z"
    live, _ = client(tmp_path, json.dumps(payload))
    with pytest.raises(LiveLLMResponseError): live.extract_requirements(implementation_doc="x", run_id="RUN-001", source_artifact_ids=["ART-001"])


def test_key_required_only_without_injection(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    LiveLLMClient(SimpleNamespace(responses=Responses("{}")))
    with pytest.raises(LiveLLMConfigurationError): LiveLLMClient()


def test_invalid_run_id_is_rejected_before_model_call(tmp_path):
    live, responses = client(tmp_path, json.dumps(manifest()))
    with pytest.raises(ValueError, match="invalid run_id"):
        live.extract_requirements(implementation_doc="doc", run_id="../../outside", source_artifact_ids=[])
    assert responses.kwargs is None
