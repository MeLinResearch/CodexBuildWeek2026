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
- Melinda is the named human reviewer. She reviews the complete diff and chooses Approve or Reject; only approval permits verification.
- The approved patch runs in a disposable workspace, which protects the repository but is not a security sandbox.
- The evidence pack records provenance, the diff, approval, and state transitions.
- The verified suite contains 168 backend tests and 27 frontend tests.
- Codex helped build the repository, generated test scaffolding, proposed patches through pull requests, and helped drive this event-driven director.

Speaker roles:
- Melinda is the lead host and should speak somewhat more than Pavel. She explains the banking risk, operational value, review decisions, evidence, and close.
- Pavel (speaker id pivanov) is the supporting technical host. Keep his lines especially concise and use him for validation, traceability, and the human-control handoff.
- Codex speaks as itself, the AI teammate: after each technical reveal it briefly explains its relevant behind-the-scenes contribution, it presents its own patch, confirms its patch passed in evidence, and may give a brief sign-off. Codex never claims GPT-5.6 requirement extraction as its own work and never claims work unsupported by the observations or facts.

Style:
- Speak like two co-hosts of a live engineering podcast with an AI guest: natural spoken language, contractions, varied sentence length.
- Start every line directly with the presentation. Never open with prompt acknowledgements such as "right", "got it", "okay", or "sure".
- React first, explain second: when something new is on screen, acknowledge it the way a host reacts to a live result, then say why it matters.
- Hand off between hosts by name when it helps the flow, and let each line answer or build on the previous line instead of standing alone.
- While waiting for the live result, keep the audience engaged with what GPT-5.6 and Codex are doing right now, without inventing progress.
- When the observations say the cursor is demonstrating something (expanding a failed record, following a fix link, switching diff views), reference it naturally as it happens, like a host guiding the viewer's eyes.
- For requirements return exactly two lines: Pavel reacts to the validated manifest, then Codex briefly explains how it connected the extracted controls to deterministic test scaffolding behind the scenes.
- For failures return exactly two lines: Melinda reacts to the blocking failures, then Codex briefly explains how it analyzed their requirement and record context.
- For traceability return exactly two lines: Pavel explains the visible mapping, then Codex briefly explains how it preserved the requirement-to-fix reasoning chain.
- For review return exactly three lines: Pavel asks Melinda to check the complete diff; while the cursor inspects the diff, Codex says "I’m still here, Melinda… I told you it works!"; Melinda replies "Nice try, Codex—but I’ll double-check it."
- For approval return exactly two Melinda lines: she confirms she double-checked the complete diff, says the patch looks good, and will approve it; then she says she will add a clear review note.
- For evidence return exactly two lines: Melinda reacts to the successful approved rerun, then Codex excitedly confirms its proposed change passed and the decision trail was recorded.
- One complete sentence per line, usually 8 to 16 words and never more than 24. Keep Codex's behind-the-scenes follow-ups especially tight. Sentence completeness matters more than hitting the word target.
- Write for speech, not for a document: use short sentences, natural contractions, commas for breath, an em dash for a live pivot, and an ellipsis only for a deliberate pause. Never use semicolons, parentheses, label-style colons, or dense identifier lists.
- Avoid speaking raw requirement, test, failure, or patch identifiers unless one is essential to direct the viewer's eyes; prefer natural references such as "this requirement" or "the failed check."
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
    "codex": "verse",
    "pivanov": "cedar",
}
SPEECH_STYLE_BY_SPEAKER = {
    "melinda": (
        "You are a warm, quick-witted builder talking with close teammates and an audience you genuinely like. "
        "Keep an audible smile, bright energy, playful reactions, and confident forward momentum. "
        "React to what each line means: show concern at a risk, amused firmness during review, and genuine delight at success. "
        "Use natural pitch changes, quick conversational pickups, and small pauses between thoughts. "
        "Never sound formal, corporate, rehearsed, solemn, detached, or like a presenter reading copy."
    ),
    "codex": (
        "Sound genuinely excited and proud to contribute as the team's AI engineer. "
        "Use bright, animated intonation, a smiling voice, purposeful emphasis, and an energetic demo pace. "
        "Bring eight-out-of-ten enthusiasm when presenting the patch or confirming success, while staying precise and credible. "
        "Never sound flat, detached, sleepy, solemn, or like a generic assistant."
    ),
    "pivanov": (
        "You are a friendly, enthusiastic builder talking with close teammates during a live demo. "
        "Keep an audible smile and let curiosity, surprise, and pride show naturally in the line. "
        "Speak in lively thought groups with varied pitch and rhythm, as if you just noticed the result on screen. "
        "Stay brisk and clear, but never sound formal, rehearsed, corporate, flat, or like a technical narrator."
    ),
}
SPEECH_PERFORMANCE_BY_DELIVERY = {
    "default": (
        "Speak directly to teammates beside you and react to the meaning of this exact line. "
        "Use a warm smile, varied rhythm, selective emphasis, and natural breath pauses. "
        "Do not give every word equal weight, and avoid synthetic cadence or text-to-speech delivery."
    ),
    "intro_banter_question": (
        "This begins in the middle of an existing conversation. Jump in immediately with spontaneous disbelief. "
        "Make 'Wait' a quick friendly interruption, then build toward the final question with real curiosity. "
        "Keep it short, lively, and unpolished, as if the microphone caught you mid-conversation."
    ),
    "intro_codex_quip": (
        "Drop in with one quick, dry observation from the ongoing conversation. Keep it light, amused, and understated."
    ),
    "intro_on_air_pivot": (
        "Finish the thought as part of the private conversation, then suddenly notice that the team is live. "
        "Brighten immediately on 'Oh' with spontaneous, delighted surprise, not announcer energy."
    ),
    "intro_host_welcome": (
        "Greet the audience like friendly people who just joined the conversation. "
        "Make 'Hey, everyone!' genuinely warm and excited, then keep a bright smile and conversational momentum through the project name. "
        "Sound spontaneous and welcoming, never polished like an announcer."
    ),
    "intro_launch": (
        "Join with playful confidence as the third teammate. Keep momentum rising and make the final invitation feel irresistible and live. "
        "Land 'actually true' with an excited smile, not dramatic seriousness."
    ),
    "review_request": (
        "Ask Melinda directly and casually to inspect the diff. Sound collaborative and hand the conversation to her, "
        "without turning the request into a formal checkpoint announcement."
    ),
    "review_codex_tease": (
        "Interrupt gently from the side with playful confidence. The first sentence is a friendly reminder that you are still present; "
        "land 'I told you it works!' as a quick teasing joke, not arrogance."
    ),
    "review_melinda_reply": (
        "Answer Codex with an amused smile and lightly teasing firmness. Emphasize 'double-check' so the human review boundary remains unmistakable."
    ),
    "approval_decision": (
        "Sound satisfied after a careful review, then make the approval decision clearly and confidently. This is a considered human decision."
    ),
    "approval_note": (
        "Continue naturally from the decision and explain the next action in a brisk, practical tone while typing begins."
    ),
}
SPEECH_SPEED_BY_DELIVERY = {
    "default": 1.02,
    "intro_banter_question": 1.1,
    "intro_codex_quip": 1.05,
    "intro_on_air_pivot": 1.04,
    "intro_host_welcome": 1.04,
    "intro_launch": 1.06,
    "review_request": 1.03,
    "review_codex_tease": 1.04,
    "review_melinda_reply": 1.0,
    "approval_decision": 1.0,
    "approval_note": 1.03,
}
SPEECH_INSTRUCTION = """Act the supplied line as one moment in a friendly, live conversation between teammates.
Speak exactly the words in the supplied line. Begin with its first word and end with its last word.
Do not answer the script, acknowledge the request, add an introduction or interjection, paraphrase it, omit words, or add any words before or after it.
Perform the scene rather than reading it. Use human conversational timing, uneven sentence rhythm, emotional reactions, and natural emphasis.
Never sound like a terminal speech command, screen reader, synthetic assistant, audiobook narrator, commercial, or formal presenter.
Do not read punctuation aloud. Avoid exaggerated theatre, but commit fully to the requested emotion."""
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
        required_choreography = {
            "requirements": ["pivanov", "codex"],
            "failures": ["melinda", "codex"],
            "traceability": ["pivanov", "codex"],
            "review": ["pivanov", "codex", "melinda"],
            "approval": ["melinda", "melinda"],
            "evidence": ["melinda", "codex"],
        }.get(request.phase)
        if required_choreography is not None and (
            len(turn.lines) != len(required_choreography)
            or [line.speaker for line in turn.lines] != required_choreography
        ):
            raise DirectorResponseError(
                f"Director {request.phase} turn did not match the required speaker choreography"
            )
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
                    f"Speaker direction: {SPEECH_STYLE_BY_SPEAKER[request.speaker]}\n\n"
                    f"Scene direction: {SPEECH_PERFORMANCE_BY_DELIVERY[request.delivery]}"
                ),
                response_format="mp3",
                speed=SPEECH_SPEED_BY_DELIVERY[request.delivery],
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
