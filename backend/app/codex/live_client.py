from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from app import config
from app.codex.client import CodexProposalRequest
from app.codex.validate import CodexValidationError, validate_patch_proposal
from app.llm.client import JsonObject

CODEX_INSTRUCTION = "You are the read-only Codex patch proposal boundary for Release Assurance. Do not edit, create, delete, rename, or apply repository files. Do not run commands that write to the repository. Inspect only what is necessary. Return exactly one JSON object matching patch_proposal.schema.json. The diff must be a unified git diff and may target only the supplied allowed paths. Copy all supplied IDs and provenance values exactly. Set status to pending. Include full unmodified context lines in every hunk so the diff applies cleanly with git apply. Do not include markdown or explanatory text."


class CodexExecutionError(RuntimeError):
    pass


class LiveCodexClient:
    def __init__(self, runner: Callable[..., Any] = subprocess.run, executable: str | None = None,
                 timeout: int | None = None, quarantine_root: Path | None = None,
                 max_diff_bytes: int | None = None) -> None:
        self.runner = runner
        self.executable = executable or config.CODEX_EXECUTABLE
        self.timeout = timeout or config.CODEX_TIMEOUT_SECONDS
        self.quarantine_root = quarantine_root or config.QUARANTINE_DIR
        self.max_diff_bytes = max_diff_bytes or config.CODEX_MAX_DIFF_BYTES

    def _failure(self, summary: str, path: Path) -> CodexExecutionError:
        return CodexExecutionError(f"{summary}; quarantine: {path}")

    def propose_patch(self, request: CodexProposalRequest) -> JsonObject:
        quarantine = self.quarantine_root / "codex" / request.run_id / request.patch_id / f"{request.attempt:03d}"
        quarantine.mkdir(parents=True, exist_ok=True)
        proposal_path = quarantine / "proposal.raw.json"
        # The exact provenance block the validator will demand; the instruction
        # says "copy provenance exactly", so it must be supplied verbatim or the
        # model has to guess fields like validation_status (and gets them wrong).
        provenance = {"run_id": request.run_id, "schema_version": request.schema_version,
                      "source_artifact_ids": list(request.source_artifact_ids), "created_at": request.created_at,
                      "producer": "codex", "mode": "live", "client": "LiveCodexClient",
                      "validation_status": "validated"}
        context = {"run_id": request.run_id, "patch_id": request.patch_id,
                   "failure_ids": list(request.failure_ids), "allowed_paths": list(request.allowed_paths),
                   "source_artifact_ids": list(request.source_artifact_ids), "schema_version": request.schema_version,
                   "created_at": request.created_at, "provenance": provenance, "task_context": request.task_context}
        prompt = f"{CODEX_INSTRUCTION}\n{json.dumps(context, separators=(',', ':'))}"
        command = [self.executable, "-a", "never", "exec", "--ephemeral", "--ignore-user-config",
                   "--cd", str(request.repo_path), "--sandbox", "read-only", "--color", "never", "--json",
                   "--output-last-message", str(proposal_path), "-"]
        try:
            result = self.runner(command, cwd=request.repo_path, input=prompt, text=True,
                                 capture_output=True, timeout=self.timeout, check=False, shell=False)
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout if isinstance(error.stdout, str) else ""
            stderr = error.stderr if isinstance(error.stderr, str) else ""
            self._write_logs(quarantine, stdout, stderr)
            raise self._failure("Codex execution timed out", quarantine) from error
        self._write_logs(quarantine, result.stdout or "", result.stderr or "")
        if result.returncode != 0:
            raise self._failure("Codex execution failed", quarantine)
        if not proposal_path.is_file():
            raise self._failure("Codex did not produce a proposal", quarantine)
        raw = proposal_path.read_text(encoding="utf-8")
        try:
            payload: Any = json.loads(raw)
        except json.JSONDecodeError as error:
            raise self._failure("Codex proposal was not valid JSON", quarantine) from error
        if not isinstance(payload, dict):
            raise self._failure("Codex proposal was not a JSON object", quarantine)
        try:
            return validate_patch_proposal(payload, request, self.max_diff_bytes)
        except CodexValidationError as error:
            raise self._failure("Codex proposal failed validation", quarantine) from error

    @staticmethod
    def _write_logs(quarantine: Path, stdout: str, stderr: str) -> None:
        (quarantine / "events.jsonl").write_text(stdout, encoding="utf-8")
        key = os.environ.get("OPENAI_API_KEY")
        if key:
            stderr = stderr.replace(key, "[REDACTED]")
        stderr = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", stderr)
        (quarantine / "stderr.log").write_text(stderr, encoding="utf-8")
