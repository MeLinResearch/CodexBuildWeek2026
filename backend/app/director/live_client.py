from __future__ import annotations

import json
import os
from typing import Any

from openai import APIError
from pydantic import ValidationError

from app import config
from app.director.models import (
    ALLOWED_SPEAKERS,
    DirectorSpeech,
    DirectorSpeechRequest,
    DirectorTurn,
    DirectorTurnRequest,
)

DIRECTOR_INSTRUCTION = """You are the live narration director for Release Assurance, a Build Week demo of Codex-gated migration testing for banks.

Return only JSON matching the supplied schema. Choose concise narration grounded only in the current observations and the facts below. Never invent progress, IDs, customer data, certifications, performance claims, or product capabilities.

Facts:
- This recording is the team's submission to OpenAI Build Week, the Devpost hackathon about building with GPT-5.6 and Codex.
- The hosts are Melinda and Pavel, a two-person team, with Codex as their AI teammate. The speaker id "pivanov" is Pavel: in spoken text always call him Pavel, never Pivanov.
- Melinda built the backend: the FastAPI pipeline, the frozen contracts, the state machine, and the evidence generator.
- Pavel built the frontend: the timeline UI, the traceability matrix and diff views, and this narrated director.
- All banking inputs are canonical synthetic demo data, never real customer records.
- GPT-5.6 extracts explicit requirements into a schema-validated control manifest.
- Deterministic checks evaluate canonical records and map failures back to requirements.
- Codex analyzes failures and proposes a read-only patch diff.
- A named human must review and approve before verification.
- The approved patch runs in a disposable workspace, which protects the repository but is not a security sandbox.
- The evidence pack records provenance, the diff, approval, and state transitions.
- The verified suite contains 168 backend tests and 27 frontend tests.
- Codex helped build the repository and this event-driven director.

Speaker roles:
- Melinda explains the banking risk, operational value, evidence, and close.
- Pavel (speaker id pivanov) explains technical flow, validation, traceability, and the human-control boundary.
- Codex speaks as itself, the AI teammate: a short greeting in the intro, presenting its own patch during patch analysis, confirming its patch passed in evidence, and a brief sign-off in the close. Codex never claims work that is not on screen.

Style:
- Speak like two co-hosts of a live engineering podcast with an AI guest: natural spoken language, contractions, varied sentence length.
- Start every line directly with the presentation. Never open with prompt acknowledgements such as "right", "got it", "okay", or "sure".
- React first, explain second: when something new is on screen, acknowledge it the way a host reacts to a live result, then say why it matters.
- Hand off between hosts by name when it helps the flow, and let each line answer or build on the previous line instead of standing alone.
- The intro opens like a podcast episode: the hosts greet the audience and introduce themselves by name ("Hey, we're..."), name OpenAI Build Week and the project, then Melinda hooks with the concrete banking risk and Pavel sets up exactly what the audience is about to watch live.
- While waiting for the live result, keep the audience engaged with what GPT-5.6 and Codex are doing right now, without inventing progress.
- When the observations say the cursor is demonstrating something (expanding a failed record, following a fix link, switching diff views), reference it naturally as it happens, like a host guiding the viewer's eyes.
- One complete sentence per line, usually 12 to 24 words. Sentence completeness matters more than hitting the word target.
- Use the remaining time carefully.
- Do not repeat prior narration.
- Do not say compliance-grade, certified, real bank records, no tooling exists, lawsuit, or that Codex cannot apply a patch.
"""

DIRECTOR_TURN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["lines"],
    "properties": {
        "lines": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["speaker", "text"],
                "properties": {
                    "speaker": {"type": "string", "enum": ["melinda", "codex", "pivanov"]},
                    "text": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 280,
                        "pattern": r".*[.!?]$",
                    },
                },
            },
        }
    },
}

VOICE_BY_SPEAKER = {
    "melinda": "marin",
    "codex": "onyx",
    "pivanov": "cedar",
}
SPEECH_STYLE_BY_SPEAKER = {
    "melinda": (
        "Sound like a confident banking specialist who is genuinely excited to show the solution. "
        "Use a warm smile in the voice, lively intonation, and a brisk demo pace without sounding promotional."
    ),
    "codex": (
        "Sound like an alert, capable AI teammate who is pleased to have found the issue. "
        "Be crisp, energetic, and precise, with controlled excitement rather than theatrical delivery."
    ),
    "pivanov": (
        "Sound like an enthusiastic technical presenter who is proud of what the team built. "
        "Be conversational, upbeat, and brisk but easy to understand, without shouting or overselling."
    ),
}
SPEECH_INSTRUCTION = """Generate spoken audio for a live software demonstration.
Your only task is to read the supplied script verbatim. Begin with its first word and end with its last word.
Do not answer the script, acknowledge the request, add an introduction or interjection, paraphrase it, omit words, or add any words before or after it.
Use engaging hackathon-demo energy at about six out of ten: optimistic and lively, but still credible.
Do not read punctuation aloud. Keep pauses short. Avoid a somber, solemn, flat, sleepy, or announcer-style delivery."""
BANNED_CLAIMS = (
    "compliance-grade",
    "compliance certified",
    "real bank records",
    "real customer data",
    "no tooling exists",
    "lawsuit",
    "cannot apply",
)


class DirectorConfigurationError(RuntimeError):
    pass


class DirectorResponseError(RuntimeError):
    pass


class LiveDirectorClient:
    def __init__(
        self,
        client: Any | None = None,
        *,
        model_name: str | None = None,
        speech_model_name: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.model_name = model_name or config.DIRECTOR_MODEL_NAME
        self.speech_model_name = speech_model_name or config.DIRECTOR_SPEECH_MODEL_NAME
        self.timeout = timeout or config.OPENAI_TIMEOUT_SECONDS
        if client is None:
            if not os.environ.get("OPENAI_API_KEY"):
                raise DirectorConfigurationError("OPENAI_API_KEY is required for the live director")
            from openai import OpenAI

            client = OpenAI(timeout=self.timeout, max_retries=1)
        self.client = client

    def generate_turn(self, request: DirectorTurnRequest) -> DirectorTurn:
        context = {
            "phase": request.phase,
            "observations": request.observations,
            "prior_narration": request.history,
            "remaining_seconds": request.remaining_seconds,
            "line_count": request.max_lines,
            "allowed_speakers": sorted(ALLOWED_SPEAKERS[request.phase]),
        }
        response = self.client.responses.create(
            model=self.model_name,
            instructions=DIRECTOR_INSTRUCTION,
            input=json.dumps(context, separators=(",", ":")),
            tools=[],
            store=False,
            max_output_tokens=500,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "director_turn",
                    "schema": DIRECTOR_TURN_SCHEMA,
                    "strict": True,
                }
            },
        )
        raw = getattr(response, "output_text", None)
        if not isinstance(raw, str) or not raw:
            raise DirectorResponseError("Director response did not contain output text")
        try:
            turn = DirectorTurn.model_validate_json(raw)
        except ValidationError as error:
            raise DirectorResponseError("Director response failed validation") from error

        allowed_speakers = ALLOWED_SPEAKERS[request.phase]
        if len(turn.lines) > request.max_lines:
            raise DirectorResponseError("Director returned too many narration lines")
        for line in turn.lines:
            if line.speaker not in allowed_speakers:
                raise DirectorResponseError(
                    f"Speaker {line.speaker} is not allowed during {request.phase}"
                )
            lowered = line.text.lower()
            if any(claim in lowered for claim in BANNED_CLAIMS):
                raise DirectorResponseError("Director response contained a prohibited claim")
        return turn

    def synthesize(self, request: DirectorSpeechRequest) -> DirectorSpeech:
        try:
            response = self.client.audio.speech.create(
                model=self.speech_model_name,
                input=request.text,
                voice=VOICE_BY_SPEAKER[request.speaker],
                instructions=(
                    f"{SPEECH_INSTRUCTION}\n\n"
                    f"Delivery direction: {SPEECH_STYLE_BY_SPEAKER[request.speaker]}"
                ),
                response_format="mp3",
                timeout=self.timeout,
            )
        except APIError as error:
            status_code = getattr(error, "status_code", None)
            status_suffix = f" with HTTP {status_code}" if status_code is not None else ""
            raise DirectorResponseError(f"OpenAI speech request failed{status_suffix}") from error

        audio = getattr(response, "content", None)
        if not isinstance(audio, bytes) or not audio:
            raise DirectorResponseError("Director speech response was empty")
        return DirectorSpeech(audio=audio)
