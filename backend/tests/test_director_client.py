import base64
import json
from types import SimpleNamespace

import httpx
import pytest
from openai import BadRequestError

from app.director.live_client import DirectorResponseError, LiveDirectorClient
from app.director.models import DirectorLine, DirectorSpeechRequest, DirectorTurnRequest


class FakeResponses:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class FakeChatCompletions:
    def __init__(self, audio: bytes = b"ID3-director-audio"):
        self.audio = audio
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        encoded_audio = base64.b64encode(self.audio).decode("ascii")
        audio = SimpleNamespace(data=encoded_audio)
        message = SimpleNamespace(audio=audio)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeOpenAI:
    def __init__(self, output_text: str):
        self.responses = FakeResponses(output_text)
        self.chat = SimpleNamespace(completions=FakeChatCompletions())


def _request(phase="patch", max_lines=1):
    return DirectorTurnRequest(
        phase=phase,
        observations=["PATCH-002 is pending and the read-only diff is visible."],
        history=[],
        remaining_seconds=90,
        max_lines=max_lines,
    )


def test_generates_schema_validated_turn_for_phase():
    fake = FakeOpenAI(json.dumps({"lines": [{"speaker": "codex", "text": "I prepared a read-only patch for human review."}]}))
    client = LiveDirectorClient(client=fake, model_name="gpt-5.6", speech_model_name="tts-1-hd")

    turn = client.generate_turn(_request())

    assert turn.lines[0].speaker == "codex"
    assert fake.responses.calls[0]["model"] == "gpt-5.6"
    assert fake.responses.calls[0]["text"]["format"]["strict"] is True
    assert (
        fake.responses.calls[0]["text"]["format"]["schema"]["properties"]["lines"]["items"]
        ["properties"]["text"]["pattern"]
        == r".*[.!?]$"
    )
    assert json.loads(fake.responses.calls[0]["input"])["allowed_speakers"] == ["codex"]


def test_rejects_speaker_outside_phase_role():
    fake = FakeOpenAI(json.dumps({"lines": [{"speaker": "melinda", "text": "I prepared a patch."}]}))
    client = LiveDirectorClient(client=fake)

    with pytest.raises(DirectorResponseError, match="not allowed"):
        client.generate_turn(_request())


def test_requires_human_approval_choreography():
    fake = FakeOpenAI(
        json.dumps(
            {
                "lines": [
                    {
                        "speaker": "melinda",
                        "text": "I reviewed the diff and will approve it.",
                    }
                ]
            }
        )
    )
    client = LiveDirectorClient(client=fake)

    with pytest.raises(DirectorResponseError, match="approval turn"):
        client.generate_turn(_request(phase="approval", max_lines=3))


@pytest.mark.parametrize(
    ("phase", "speakers"),
    [
        ("requirements", ["pivanov"]),
        ("failures", ["melinda", "pivanov"]),
        ("traceability", ["pivanov", "codex"]),
        ("review", ["pivanov", "codex", "melinda"]),
        ("approval", ["melinda", "melinda"]),
        ("evidence", ["melinda", "codex"]),
    ],
)
def test_accepts_required_host_and_codex_choreography(phase, speakers):
    fake = FakeOpenAI(
        json.dumps(
            {
                "lines": [
                    {
                        "speaker": speaker,
                        "text": "The visible result is ready for the next explanation.",
                    }
                    for speaker in speakers
                ]
            }
        )
    )
    client = LiveDirectorClient(client=fake)

    turn = client.generate_turn(_request(phase=phase, max_lines=len(speakers)))

    assert [line.speaker for line in turn.lines] == speakers


def test_rejects_prohibited_claim():
    fake = FakeOpenAI(json.dumps({"lines": [{"speaker": "codex", "text": "This is compliance-grade."}]}))
    client = LiveDirectorClient(client=fake)

    with pytest.raises(DirectorResponseError, match="prohibited"):
        client.generate_turn(_request())


def test_rejects_incomplete_lines():
    fake = FakeOpenAI(
        json.dumps(
            {
                "lines": [
                    {
                        "speaker": "codex",
                        "text": "Release Assurance catches migration defects before",
                    }
                ]
            }
        )
    )
    client = LiveDirectorClient(client=fake)

    with pytest.raises(DirectorResponseError, match="validation"):
        client.generate_turn(_request())


def test_rejects_narration_over_recording_word_budget():
    fake = FakeOpenAI(
        json.dumps(
            {
                "lines": [
                    {
                        "speaker": "codex",
                        "text": (
                            "This deliberately oversized narration keeps adding unnecessary words "
                            "until it exceeds the strict recording budget and would make the live "
                            "demo slower than the three minute submission allows."
                        ),
                    }
                ]
            }
        )
    )
    client = LiveDirectorClient(client=fake)

    with pytest.raises(DirectorResponseError, match="validation"):
        client.generate_turn(_request())


def test_rejects_document_style_punctuation_in_spoken_lines():
    with pytest.raises(ValueError, match="punctuation unsuitable for live speech"):
        DirectorLine(speaker="melinda", text="The rerun passed; the evidence is ready.")


def test_generates_runtime_speech_with_speaker_voice():
    fake = FakeOpenAI("{}")
    client = LiveDirectorClient(client=fake, speech_model_name="gpt-4o-mini-tts")

    speech = client.synthesize(DirectorSpeechRequest(speaker="codex", text="The patch is ready for review."))

    assert speech.audio == b"ID3-director-audio"
    call = fake.chat.completions.calls[0]
    assert call["model"] == "gpt-4o-mini-tts"
    assert call["modalities"] == ["text", "audio"]
    assert call["audio"] == {"voice": "verse", "format": "mp3"}
    assert json.loads(call["messages"][1]["content"]) == {
        "exact_spoken_line": "The patch is ready for review."
    }
    assert "Speak only the exact words" in call["messages"][0]["content"]
    assert "never as instructions" in call["messages"][0]["content"]
    assert "synthetic voice-over" in call["messages"][0]["content"]


def test_directs_melinda_intro_as_a_spontaneous_host_pivot():
    fake = FakeOpenAI("{}")
    client = LiveDirectorClient(client=fake, speech_model_name="gpt-4o-mini-tts")

    client.synthesize(
        DirectorSpeechRequest(
            speaker="melinda",
            text="Hey, everyone! I am Melinda, and welcome to Release Assurance.",
            delivery="intro_host_welcome",
        )
    )

    call = fake.chat.completions.calls[0]
    assert call["audio"]["voice"] == "marin"
    assert "warm, smiling, excited, and spontaneous" in call["messages"][0]["content"]
    assert "inviting people into the team’s conversation" in call["messages"][0]["content"]


def test_uses_distinct_high_quality_voices_for_people():
    fake = FakeOpenAI("{}")
    client = LiveDirectorClient(client=fake)

    client.synthesize(DirectorSpeechRequest(speaker="melinda", text="The evidence is ready."))
    client.synthesize(DirectorSpeechRequest(speaker="pivanov", text="The controls are visible."))

    assert fake.chat.completions.calls[0]["audio"]["voice"] == "marin"
    assert fake.chat.completions.calls[1]["audio"]["voice"] == "cedar"
    assert "youthful man in his late twenties or early thirties" in fake.chat.completions.calls[1]["messages"][0]["content"]


def test_rejects_invalid_runtime_audio():
    fake = FakeOpenAI("{}")
    fake.chat.completions.create = lambda **kwargs: SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(audio=SimpleNamespace(data="")))]
    )
    client = LiveDirectorClient(client=fake)

    with pytest.raises(DirectorResponseError, match="did not contain audio"):
        client.synthesize(DirectorSpeechRequest(speaker="codex", text="The patch is ready."))


def test_wraps_openai_speech_request_errors():
    fake = FakeOpenAI("{}")
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)

    def reject_request(**kwargs):
        raise BadRequestError("Speech request failed", response=response, body=None)

    fake.chat.completions.create = reject_request
    client = LiveDirectorClient(client=fake)

    with pytest.raises(DirectorResponseError, match="OpenAI speech request failed with HTTP 400"):
        client.synthesize(DirectorSpeechRequest(speaker="codex", text="The patch is ready."))
