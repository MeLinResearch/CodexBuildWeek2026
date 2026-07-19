from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = (REPO_ROOT / "contracts" / "VERSION").read_text(encoding="utf-8").strip()
FIXTURES_DIR = REPO_ROOT / "fixtures"
API_FIXTURES_DIR = FIXTURES_DIR / "api"
DB_PATH = Path(os.environ.get("RELEASE_ASSURANCE_DB_PATH", REPO_ROOT / "release_assurance.sqlite"))


def _positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a positive integer") from error
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


GPT_MODEL_NAME = os.environ.get("RELEASE_ASSURANCE_GPT_MODEL", "gpt-5.6")
DIRECTOR_MODEL_NAME = os.environ.get("RELEASE_ASSURANCE_DIRECTOR_MODEL", GPT_MODEL_NAME)
DIRECTOR_SPEECH_MODEL_NAME = os.environ.get(
    "RELEASE_ASSURANCE_DIRECTOR_SPEECH_MODEL",
    "gpt-audio-1.5",
)
OPENAI_TIMEOUT_SECONDS = _positive_int_env("RELEASE_ASSURANCE_OPENAI_TIMEOUT_SECONDS", 120)
CODEX_EXECUTABLE = os.environ.get("RELEASE_ASSURANCE_CODEX_EXECUTABLE", "codex")
CODEX_TIMEOUT_SECONDS = _positive_int_env("RELEASE_ASSURANCE_CODEX_TIMEOUT_SECONDS", 180)
CODEX_MAX_DIFF_BYTES = _positive_int_env("RELEASE_ASSURANCE_CODEX_MAX_DIFF_BYTES", 100000)
QUARANTINE_DIR = REPO_ROOT / ".release_assurance" / "quarantine"
LIVE_RUNS_DIR = REPO_ROOT / ".release_assurance" / "runs"
CODEX_TASK_ID_FIXTURE = "fixture"
RUN_ID_FIXTURE = "RUN-001"
PATCH_ID_FIXTURE = "PATCH-001"
FIXTURE_CLOCK_AT = "2026-07-12T00:00:00Z"


def fixture_clock() -> str:
    return FIXTURE_CLOCK_AT


def default_clock() -> str:
    fixed_clock = os.environ.get("FIXED_CLOCK")
    if fixed_clock is not None:
        return fixed_clock
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_sequential_id_generator(prefix: str = "", start: int = 1) -> Callable[[str], str]:
    counters: dict[str, int] = {}

    def generate(requested_prefix: str) -> str:
        effective_prefix = requested_prefix or prefix
        if not effective_prefix:
            raise ValueError("ID prefix is required")
        current = counters.get(effective_prefix, start)
        counters[effective_prefix] = current + 1
        return f"{effective_prefix}-{current:03d}"

    return generate
