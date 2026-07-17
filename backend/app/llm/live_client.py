from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from app import config
from app.llm.client import JsonObject
from app.llm.validate import LLMValidationError, bundle_schema_for_model, validate_output

SYSTEM_INSTRUCTION = "You are the requirements extraction boundary for Release Assurance. Return only one JSON object matching the supplied schema. Extract only requirements explicitly stated in the implementation document. Do not invent or infer requirements. Preserve requirement wording in lowercase without terminal punctuation. Assign REQ-001 onward in document order. Use only the rule_type values permitted by the schema. Copy every supplied metadata and provenance value exactly."


class LiveLLMConfigurationError(RuntimeError):
    pass


class LiveLLMResponseError(RuntimeError):
    pass


class LiveLLMClient:
    def __init__(self, client: Any | None = None, clock: Callable[[], str] = config.default_clock,
                 quarantine_root: Path | None = None, model_name: str | None = None,
                 timeout: int | None = None) -> None:
        self.clock = clock
        self.quarantine_root = quarantine_root or config.QUARANTINE_DIR
        self.model_name = model_name or config.GPT_MODEL_NAME
        self.timeout = timeout or config.OPENAI_TIMEOUT_SECONDS
        if client is None:
            if not os.environ.get("OPENAI_API_KEY"):
                raise LiveLLMConfigurationError("OPENAI_API_KEY is required for LiveLLMClient")
            from openai import OpenAI
            client = OpenAI(timeout=self.timeout, max_retries=1)
        self.client = client

    def extract_requirements(self, *, implementation_doc: str, run_id: str,
                             source_artifact_ids: list[str]) -> JsonObject:
        created_at = self.clock()
        provenance = {"producer": "gpt-5.6", "mode": "live", "client": "LiveLLMClient",
                      "validation_status": "validated"}
        context = {"implementation_doc": implementation_doc, "run_id": run_id,
                   "source_artifact_ids": source_artifact_ids, "schema_version": config.SCHEMA_VERSION,
                   "created_at": created_at, "provenance": provenance}
        response = self.client.responses.create(
            model=self.model_name,
            instructions=SYSTEM_INSTRUCTION,
            input=json.dumps(context, separators=(",", ":")),
            tools=[], store=False, max_output_tokens=4000,
            text={"format": {"type": "json_schema", "name": "control_manifest",
                             "schema": bundle_schema_for_model("control_manifest.schema.json"),
                             "strict": True}},
        )
        raw = getattr(response, "output_text", None)
        if not isinstance(raw, str) or not raw:
            raise LiveLLMResponseError("Live LLM response did not contain output text")
        raw_path = self.quarantine_root / "llm" / run_id / "control_manifest.raw.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(raw, encoding="utf-8")
        try:
            payload: Any = json.loads(raw)
        except json.JSONDecodeError as error:
            raise LiveLLMResponseError("Live LLM response was not valid JSON") from error
        if not isinstance(payload, dict):
            raise LiveLLMResponseError("Live LLM response must be a JSON object")
        try:
            validate_output("control_manifest.schema.json", payload)
            expected = {"run_id": run_id, "schema_version": config.SCHEMA_VERSION,
                        "source_artifact_ids": source_artifact_ids, "created_at": created_at, **provenance}
            blocks = [payload.get("provenance")] + [item.get("provenance") for item in payload.get("requirements", [])]
            if payload.get("run_id") != run_id or any(not isinstance(block, dict) or any(block.get(k) != v for k, v in expected.items()) for block in blocks):
                raise LiveLLMResponseError("Live LLM response metadata did not match the request")
        except LLMValidationError as error:
            raise LiveLLMResponseError("Live LLM response failed contract validation") from error
        return payload
