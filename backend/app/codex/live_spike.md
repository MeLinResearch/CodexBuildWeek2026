# Codex Operational Spike

Status: REVIEW_REQUIRED

Date: 2026-07-14

## Purpose

This spike records whether real Codex can safely support the live Devpost demo path.

It does not implement LiveCodexClient.
It does not wire Codex into the API.
It does not apply patches.
It does not change contracts, frontend, fixtures, reconcile, or pipeline behavior.

Do not implement LiveCodexClient until this spike is reviewed.

## Decision

Pending human review.

## Fallback if blocked

If checks 1 through 6 cannot be proven, keep the submitted demo on deterministic fixture mode and describe live Codex integration as deferred.

If checks 1 through 6 pass but checks 7 or 8 fail, the accepted fallback is:

Codex proposal plus controlled manual apply, honestly labeled in README and demo narration.

## Commands attempted

Record every command attempted here with the exact command, exit code, and short result.

Example format:

- `command -v codex`
  - exit: `1`
  - result: `No codex executable was found on PATH in this environment.`
- `codex --version`
  - exit: `127`
  - result: `The shell reported codex: command not found, so the installed version could not be inspected.`
- `codex exec --help`
  - exit: `127`
  - result: `The shell reported codex: command not found, so non-interactive exec help could not be inspected.`

## Spike checks

### 1. codex exec runs non-interactively

Status: BLOCKED

Evidence:
- `command -v codex` exited 1 and found no codex executable on PATH.
- `codex exec --help` exited 127 because the shell reported `codex: command not found`.
- This behavior cannot be proven until Codex CLI is installed and authenticated in an environment where `codex exec` can be invoked.

### 2. read-only inspection can be forced

Status: BLOCKED

Evidence:
- Codex CLI is not available in this environment, so read-only or sandbox flags could not be inspected or exercised.
- This behavior cannot be proven until a real Codex CLI invocation can demonstrate read-only inspection without writing files.

### 3. task context can be resumed or persisted

Status: BLOCKED

Evidence:
- Codex CLI is not available in this environment, so resume, session, or persistence behavior could not be inspected or exercised.
- This behavior cannot be proven until a real Codex CLI invocation can demonstrate persisted or resumable task context.

### 4. structured output or artifact path is capturable

Status: BLOCKED

Evidence:
- Codex CLI is not available in this environment, so output-format options or artifact path handling could not be inspected or exercised.
- This behavior cannot be proven until a real Codex CLI invocation can produce a captured structured result or file artifact path.

### 5. can generate tests

Status: BLOCKED

Evidence:
- Codex CLI is not available in this environment, so live test generation could not be attempted.
- This behavior cannot be proven until a real Codex CLI invocation generates test content in a controlled spike workspace.

### 6. can run tests

Status: BLOCKED

Evidence:
- Codex CLI is not available in this environment, so live test execution through Codex could not be attempted.
- This behavior cannot be proven until a real Codex CLI invocation runs tests and returns a capturable result.

### 7. can propose a patch as a diff

Status: BLOCKED

Evidence:
- Codex CLI is not available in this environment, so diff proposal behavior could not be inspected or exercised.
- This behavior cannot be proven until a real Codex CLI invocation proposes a patch as a diff without applying it.

### 8. can switch to workspace-write only after approval

Status: BLOCKED

Evidence:
- Codex CLI is not available in this environment, so approval-gated workspace-write behavior could not be inspected or exercised.
- This behavior cannot be proven until a real Codex CLI invocation demonstrates read-only operation first and workspace-write only after explicit approval.

## Review notes

This file is an operational decision record, not production code.

Next allowed backend task after human review:
- implement `backend/app/llm/` interface and validation, or
- implement Codex client interfaces only if this spike proves enough live behavior.
