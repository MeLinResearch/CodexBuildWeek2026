from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from app import config
from app.codex.client import CodexProposalRequest
from app.codex.sandbox import UnsafePatchError, validate_proposed_diff
from app.llm.client import JsonObject
from app.llm.validate import LLMValidationError, validate_output


class CodexValidationError(ValueError):
    pass


def _diff_applies_cleanly(diff: str, allowed_paths: tuple[str, ...], repo_path: Path) -> None:
    """Prove the diff really applies to the current tree, in a disposable
    workspace, before it can reach the human gate. Codex output varies and a
    diff with stale hunk context passes every static check but would fail the
    post-approval rerun, which is the worst place to fail."""
    with tempfile.TemporaryDirectory(prefix="release-assurance-apply-check-") as temporary:
        workspace = Path(temporary)
        for allowed in allowed_paths:
            source = repo_path / allowed
            if not source.is_file():
                continue
            target = workspace / allowed
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )
        subprocess.run(["git", "init", "--quiet"], cwd=workspace, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "core.autocrlf", "false"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
        patch_path = workspace / "proposal.diff"
        patch_path.write_text(diff, encoding="utf-8", newline="\n")
        # --recount because model-written hunk headers routinely misstate the
        # line counts (Codex drops trailing context but keeps the counts);
        # git infers them from the body instead. Content mismatches still fail.
        result = subprocess.run(["git", "apply", "--recount", "--check", patch_path.name],
                                cwd=workspace, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise CodexValidationError(f"proposed diff does not apply cleanly: {result.stderr.strip()}")


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
        _diff_applies_cleanly(payload["diff"], request.allowed_paths, request.repo_path)
    except (LLMValidationError, UnsafePatchError, KeyError, OSError, subprocess.SubprocessError) as error:
        raise CodexValidationError("patch proposal validation failed") from error
    return payload
