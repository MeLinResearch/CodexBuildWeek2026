from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DirectorSpeaker = Literal["melinda", "codex", "pivanov"]
DirectorSpeechDelivery = Literal[
    "default",
    "intro_banter_question",
    "intro_on_air_pivot",
    "intro_reset",
    "intro_host_welcome",
    "intro_launch",
    "intro_codex_welcome",
    "intro_run_start",
    "intro_codex_on_it",
    "review_request",
    "review_codex_tease",
    "review_melinda_reply",
    "approval_decision",
    "approval_note",
    "verify_nervous",
    "close_thanks",
    "close_signoff",
    "wait_banter",
    "reveal_requirements",
    "reveal_failures",
    "reveal_traceability",
    "patch_present",
    "reveal_evidence",
]
DirectorPhase = Literal[
    "live_wait",
    "requirements",
    "failures",
    "traceability",
    "patch",
    "review",
    "approval",
    "evidence",
    "close",
]


@dataclass(frozen=True)
class DirectorSpeech:
    audio: bytes


ALLOWED_SPEAKERS: dict[DirectorPhase, frozenset[DirectorSpeaker]] = {
    "live_wait": frozenset({"melinda", "pivanov"}),
    "requirements": frozenset({"codex", "pivanov"}),
    "failures": frozenset({"codex", "melinda"}),
    "traceability": frozenset({"codex", "pivanov"}),
    "patch": frozenset({"codex"}),
    "review": frozenset({"codex", "melinda", "pivanov"}),
    "approval": frozenset({"melinda"}),
    "evidence": frozenset({"codex", "melinda"}),
    "close": frozenset({"codex", "melinda"}),
}


def _clean_bounded_text(value: str, *, field_name: str, maximum_characters: int) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    if len(cleaned) > maximum_characters:
        raise ValueError(f"{field_name} must not exceed {maximum_characters} characters")
    return cleaned


class DirectorTurnRequest(BaseModel):
    phase: DirectorPhase
    observations: list[str] = Field(min_length=1, max_length=12)
    history: list[str] = Field(default_factory=list, max_length=12)
    remaining_seconds: int = Field(ge=10, le=180)
    max_lines: int = Field(default=1, ge=1, le=3)

    @field_validator("observations")
    @classmethod
    def validate_observations(cls, values: list[str]) -> list[str]:
        return [
            _clean_bounded_text(value, field_name="observation", maximum_characters=500)
            for value in values
        ]

    @field_validator("history")
    @classmethod
    def validate_history(cls, values: list[str]) -> list[str]:
        return [
            _clean_bounded_text(value, field_name="history item", maximum_characters=350)
            for value in values
        ]


class DirectorLine(BaseModel):
    speaker: DirectorSpeaker
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = _clean_bounded_text(value, field_name="narration", maximum_characters=280)
        if len(cleaned.split()) > 24:
            raise ValueError("narration must not exceed 24 words")
        if any(punctuation in cleaned for punctuation in ("—", "–", ";", "(", ")", "[", "]", "{", "}")):
            raise ValueError("narration contains punctuation unsuitable for live speech")
        if cleaned[-1] not in ".!?":
            raise ValueError("narration must be a complete sentence")
        return cleaned


class DirectorTurn(BaseModel):
    lines: list[DirectorLine] = Field(min_length=1, max_length=3)


class DirectorSpeechRequest(BaseModel):
    speaker: DirectorSpeaker
    text: str
    delivery: DirectorSpeechDelivery = "default"

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return DirectorLine(speaker="pivanov", text=value).text
