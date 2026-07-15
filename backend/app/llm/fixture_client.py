from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import FIXTURES_DIR
from app.llm.client import JsonObject
from app.llm.validate import validate_output

CONTROL_MANIFEST_FIXTURE = FIXTURES_DIR / "model_outputs" / "control_manifest.fixture.json"
CONTROL_MANIFEST_SCHEMA = "control_manifest.schema.json"


class FixtureLLMClient:
    """Fixture-backed LLM boundary client for deterministic local development."""

    def __init__(self, fixture_path: Path | None = None) -> None:
        self.fixture_path = CONTROL_MANIFEST_FIXTURE if fixture_path is None else fixture_path

    def extract_requirements(
        self,
        *,
        implementation_doc: str,
        run_id: str,
        source_artifact_ids: list[str],
    ) -> JsonObject:
        del implementation_doc, run_id, source_artifact_ids
        with self.fixture_path.open(encoding="utf-8") as handle:
            payload: Any = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object in {self.fixture_path}")
        return validate_output(CONTROL_MANIFEST_SCHEMA, payload)
