from fastapi.testclient import TestClient

from app.director.live_client import DirectorConfigurationError
from app.director.models import DirectorLine, DirectorSpeech, DirectorTurn
from app.main import app
from app.routers import director

client = TestClient(app)


class FakeDirectorClient:
    def generate_turn(self, request):
        return DirectorTurn(lines=[DirectorLine(speaker="pivanov", text=f"The {request.phase} phase is ready.")])

    def synthesize(self, request):
        return DirectorSpeech(audio=f"audio:{request.speaker}:{request.text}".encode())


def test_director_turn_endpoint_uses_validated_runtime_contract(monkeypatch):
    monkeypatch.setattr(director, "_make_director_client", FakeDirectorClient)

    response = client.post(
        "/api/director/turn",
        json={
            "phase": "requirements",
            "observations": ["REQ-004 is visible."],
            "history": [],
            "remaining_seconds": 120,
            "max_lines": 1,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "lines": [{"speaker": "pivanov", "text": "The requirements phase is ready."}]
    }


def test_director_speech_endpoint_returns_runtime_audio(monkeypatch):
    monkeypatch.setattr(director, "_make_director_client", FakeDirectorClient)

    response = client.post(
        "/api/director/speech",
        json={
            "speaker": "melinda",
            "text": "The evidence pack is ready.",
            "delivery": "intro_host_welcome",
        },
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"audio:melinda:The evidence pack is ready."


def test_director_endpoints_reject_invalid_requests(monkeypatch):
    monkeypatch.setattr(director, "_make_director_client", FakeDirectorClient)

    turn = client.post(
        "/api/director/turn",
        json={
            "phase": "unknown",
            "observations": [],
            "remaining_seconds": 2,
            "max_lines": 3,
        },
    )
    speech = client.post("/api/director/speech", json={"speaker": "unknown", "text": ""})

    assert turn.status_code == 422
    assert speech.status_code == 422


def test_director_reports_missing_configuration(monkeypatch):
    def unavailable():
        raise DirectorConfigurationError("OPENAI_API_KEY is required for the live director")

    monkeypatch.setattr(director, "_make_director_client", unavailable)

    response = client.post(
        "/api/director/turn",
        json={
            "phase": "patch",
            "observations": ["Read-only patch ready."],
            "remaining_seconds": 175,
            "max_lines": 1,
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "OPENAI_API_KEY is required for the live director"
