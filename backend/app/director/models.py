from __future__ import annotations

from dataclasses import dataclass

from typing import Literal

from pydantic import BaseModel, Field, field_validator

DirectorSpeaker = Literal["melinda", "codex", "pivanov"]
DirectorPhase = Literal[
    "intro",
    "live_wait",
    "requirements",
    "failures",
    "traceability",
    "patch",
    "approval",
    "evidence",
    "close",
]

@dataclass(frozen=True)
class DirectorSpeech:
    audio: bytes


ALLOWED_SPEAKERS: dict[DirectorPhase, frozenset[DirectorSpeaker]] = {
    "intro": frozenset({"melinda", "pivanov", "codex"}),
    "live_wait": frozenset({"melinda", "pivanov"}),
    "requirements": frozenset({"pivanov"}),
    "failures": frozenset({"melinda", "pivanov"}),
    "traceability": frozenset({"melinda", "pivanov"}),
    "patch": frozenset({"codex"}),
    "approval": frozenset({"pivanov"}),
    "evidence": frozenset({"melinda", "pivanov", "codex"}),
    "close": frozenset({"melinda", "pivanov", "codex"}),
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
        if len(cleaned.split()) > 45:
            raise ValueError("narration must not exceed 45 words")
        if cleaned[-1] not in ".!?":
            raise ValueError("narration must be a complete sentence")
        return cleaned


class DirectorTurn(BaseModel):
    lines: list[DirectorLine] = Field(min_length=1, max_length=3)


class DirectorSpeechRequest(BaseModel):
    speaker: DirectorSpeaker
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return DirectorLine(speaker="pivanov", text=value).text
