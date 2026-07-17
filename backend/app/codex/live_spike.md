# Live Codex spike

**Status: IMPLEMENTED_PENDING_LOCAL_VERIFICATION**

Human review approved implementation of the narrow read-only boundary on 2026-07-16. Unit tests exercise the subprocess contract with fakes; they do not prove that a locally installed Codex executable enforces its sandbox. No paid Codex call was made.

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
