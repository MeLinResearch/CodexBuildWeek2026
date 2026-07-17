from __future__ import annotations

from app import config
from app.codex.client import CodexProposalRequest
from app.codex.sandbox import UnsafePatchError, validate_proposed_diff
from app.llm.client import JsonObject
from app.llm.validate import LLMValidationError, validate_output


class CodexValidationError(ValueError):
    pass


def validate_patch_proposal(payload: JsonObject, request: CodexProposalRequest,
                            max_diff_bytes: int | None = None) -> JsonObject:
    try:
        validate_output("patch_proposal.schema.json", payload)
        expected = {"run_id": request.run_id, "schema_version": request.schema_version,
                    "source_artifact_ids": list(request.source_artifact_ids), "created_at": request.created_at,
                    "producer": "codex", "mode": "live", "client": "LiveCodexClient",
                    "validation_status": "validated"}
        if payload.get("run_id") != request.run_id:
            raise CodexValidationError("run_id mismatch")
        if payload.get("patch_id") != request.patch_id:
            raise CodexValidationError("patch_id mismatch")
        if payload.get("failure_ids") != list(request.failure_ids):
            raise CodexValidationError("failure_ids mismatch")
        if payload.get("status") != "pending":
            raise CodexValidationError("status must be pending")
        provenance = payload.get("provenance")
        if not isinstance(provenance, dict) or any(provenance.get(key) != value for key, value in expected.items()):
            raise CodexValidationError("provenance mismatch")
        validate_proposed_diff(payload["diff"], request.allowed_paths,
                               max_diff_bytes or config.CODEX_MAX_DIFF_BYTES)
    except (LLMValidationError, UnsafePatchError, KeyError) as error:
        raise CodexValidationError("patch proposal validation failed") from error
    return payload
