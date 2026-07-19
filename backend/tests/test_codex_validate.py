import copy

import pytest

from app.codex.client import CodexProposalRequest
from app.codex.validate import CodexValidationError, validate_patch_proposal


def request(tmp_path):
    (tmp_path / "app.py").write_bytes(b"a\r\n")
    return CodexProposalRequest(tmp_path, "RUN-001", "PATCH-001", ("FAIL-001",), ("app.py",),
                                ("ART-001",), "2026-07-12.1", "2026-07-12T00:00:00Z", "fix")


def proposal():
    return {"run_id": "RUN-001", "patch_id": "PATCH-001", "failure_ids": ["FAIL-001"],
            "diff": "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-a\n+b\n",
            "status": "pending", "provenance": {"run_id": "RUN-001", "schema_version": "2026-07-12.1",
            "source_artifact_ids": ["ART-001"], "created_at": "2026-07-12T00:00:00Z", "producer": "codex",
            "mode": "live", "client": "LiveCodexClient", "validation_status": "validated"}}


def test_valid_proposal_returns_same_object(tmp_path):
    payload = proposal()
    assert validate_patch_proposal(payload, request(tmp_path)) is payload


def test_diff_with_stale_context_is_rejected(tmp_path):
    payload = proposal()
    payload["diff"] = "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-stale\n+b\n"
    with pytest.raises(CodexValidationError):
        validate_patch_proposal(payload, request(tmp_path))


def test_diff_with_miscounted_hunk_header_is_accepted(tmp_path):
    """Codex routinely misstates hunk line counts; --recount lets git infer
    them from the body, so a coherent hunk with wrong counts still validates."""
    payload = proposal()
    payload["diff"] = "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1,3 +1,3 @@\n-a\n+b\n"
    assert validate_patch_proposal(payload, request(tmp_path)) is payload


@pytest.mark.parametrize("field,value", [("run_id", "RUN-002"), ("patch_id", "PATCH-002"),
                                          ("failure_ids", []), ("status", "approved")])
def test_mismatches_rejected(tmp_path, field, value):
    payload = proposal(); payload[field] = value
    with pytest.raises(CodexValidationError):
        validate_patch_proposal(payload, request(tmp_path))


def test_provenance_and_contract_mismatches_rejected(tmp_path):
    payload = copy.deepcopy(proposal()); payload["provenance"]["producer"] = "fixture"
    with pytest.raises(CodexValidationError): validate_patch_proposal(payload, request(tmp_path))
    payload = proposal(); payload["extra"] = True
    with pytest.raises(CodexValidationError): validate_patch_proposal(payload, request(tmp_path))
