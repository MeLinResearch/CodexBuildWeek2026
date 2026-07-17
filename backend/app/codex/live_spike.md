# Live Codex spike

**Status: IMPLEMENTED_PENDING_LOCAL_VERIFICATION**

Human review approved implementation of the narrow read-only boundary on 2026-07-16. Unit tests exercise the subprocess contract with fakes; they do not prove that a locally installed Codex executable enforces its sandbox. No paid Codex call was made.

Do not implement LiveCodexClient until this spike is reviewed. This review occurred on 2026-07-16 before implementation.

## Decision

Keep the isolated read-only boundary, but disable live use until its exact command is verified locally.

## Fallback if blocked

Use the deterministic fixture demo. Never represent fake-runner tests as proof of live Codex execution.

## Commands attempted

## Environment checks (2026-07-17)

```text
$ command -v codex
(no output)
exit=1

$ codex --version
/bin/bash: line 1: codex: command not found
exit=127

$ codex exec --help
/bin/bash: line 1: codex: command not found
exit=127
```

These checks are blocked because the executable is absent; they did not pass.

### 1. codex exec runs non-interactively

Status: BLOCKED

The executable was unavailable.

### 2. read-only inspection can be forced

Status: BLOCKED

The flags are unit tested but not locally verified.

### 3. task context can be resumed or persisted

Status: BLOCKED

The boundary is ephemeral and no live resume test was possible.

### 4. structured output or artifact path is capturable

Status: BLOCKED

The output path is tested only with a fake runner.

### 5. can generate tests

Status: BLOCKED

No live Codex call was made.

### 6. can run tests

Status: BLOCKED

No live Codex call was made.

### 7. can propose a patch as a diff

Status: BLOCKED

Diff capture is tested only with a fake runner.

### 8. can switch to workspace-write only after approval

Status: BLOCKED

Workspace-write remains unimplemented.

## Review notes

The demo remains on fixture mode until the live boundary is verified.

## Implemented read-only command contract

```text
[
  CODEX_EXECUTABLE,
  "-a",
  "never",
  "exec",
  "--ephemeral",
  "--ignore-user-config",
  "--cd",
  str(request.repo_path),
  "--sandbox",
  "read-only",
  "--color",
  "never",
  "--json",
  "--output-last-message",
  str(proposal_raw_path),
  "-"
]
```

PR 28 live wiring remains blocked until the user verifies this command locally.
