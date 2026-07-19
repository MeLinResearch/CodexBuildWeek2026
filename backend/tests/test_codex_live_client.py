import json
import subprocess
from types import SimpleNamespace

import pytest

from app.codex.client import CodexProposalRequest
from app.codex.live_client import _build_codex_command, CodexExecutionError, LiveCodexClient


def request(tmp_path):
    (tmp_path / "app.py").write_text("a\n", encoding="utf-8")
    return CodexProposalRequest(tmp_path, "RUN-001", "PATCH-001", ("FAIL-001",), ("app.py",),
                                ("ART-001",), "2026-07-12.1", "2026-07-12T00:00:00Z", "fix")


def proposal():
    return {"run_id": "RUN-001", "patch_id": "PATCH-001", "failure_ids": ["FAIL-001"], "status": "pending",
            "diff": "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-a\n+b\n",
            "provenance": {"run_id": "RUN-001", "schema_version": "2026-07-12.1", "source_artifact_ids": ["ART-001"],
            "created_at": "2026-07-12T00:00:00Z", "producer": "codex", "mode": "live", "client": "LiveCodexClient",
            "validation_status": "validated"}}


class Runner:
    def __init__(self, payload=proposal(), returncode=0): self.payload, self.returncode, self.call = payload, returncode, None
    def __call__(self, command, **kwargs):
        self.call = (command, kwargs)
        if self.payload is not None:
            path = command[-2]; open(path, "w", encoding="utf-8").write(self.payload if isinstance(self.payload, str) else json.dumps(self.payload))
        return SimpleNamespace(stdout="events\n", stderr="", returncode=self.returncode)


def test_valid_execution_contract(tmp_path):
    runner = Runner(); req = request(tmp_path); live = LiveCodexClient(runner, executable="codex-test", timeout=9, quarantine_root=tmp_path / "q")
    assert live.propose_patch(req)["patch_id"] == "PATCH-001"
    command, kwargs = runner.call
    output = tmp_path / "q/codex/RUN-001/PATCH-001/001/proposal.raw.json"
    assert command == ["codex-test", "-a", "never", "exec", "--ephemeral", "--ignore-user-config", "--cd", str(tmp_path),
                       "--sandbox", "read-only", "--color", "never", "--json", "--output-last-message", str(output), "-"]
    assert kwargs["cwd"] == tmp_path and kwargs["timeout"] == 9 and kwargs["shell"] is False
    assert kwargs["input"].startswith("You are the read-only Codex") and kwargs["text"] is True


def test_windows_npm_shim_uses_command_processor():
    assert _build_codex_command(
        "C:\\Users\\builder\\AppData\\Roaming\\npm\\codex.cmd",
        ["--version"],
        platform="nt",
        comspec="C:\\Windows\\System32\\cmd.exe",
    ) == [
        "C:\\Windows\\System32\\cmd.exe",
        "/d",
        "/s",
        "/c",
        '""C:\\Users\\builder\\AppData\\Roaming\\npm\\codex.cmd" "--version""',
    ]


def test_windows_native_codex_executable_runs_directly():
    assert _build_codex_command(
        "C:\\Tools\\codex.exe",
        ["--version"],
        platform="nt",
    ) == ["C:\\Tools\\codex.exe", "--version"]


@pytest.mark.parametrize("runner", [Runner(returncode=2), Runner(payload=None)])
def test_execution_failures_are_safe(tmp_path, runner):
    with pytest.raises(CodexExecutionError) as error: LiveCodexClient(runner, quarantine_root=tmp_path / "q").propose_patch(request(tmp_path))
    assert "quarantine" in str(error.value)


def test_timeout_is_safe(tmp_path):
    def timeout(*args, **kwargs): raise subprocess.TimeoutExpired("codex", 1, output="out", stderr="err")
    with pytest.raises(CodexExecutionError): LiveCodexClient(timeout, quarantine_root=tmp_path / "q").propose_patch(request(tmp_path))


def test_invalid_json_preserved_and_secrets_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secretkey")
    runner = Runner("bad")
    def with_secret(command, **kwargs):
        result = runner(command, **kwargs); result.stderr = "sk-secretkey sk-another"
        return result
    with pytest.raises(CodexExecutionError): LiveCodexClient(with_secret, quarantine_root=tmp_path / "q").propose_patch(request(tmp_path))
    folder = tmp_path / "q/codex/RUN-001/PATCH-001/001"
    assert (folder / "proposal.raw.json").read_text() == "bad"
    assert (folder / "stderr.log").read_text() == "[REDACTED] [REDACTED]"
