# Release Assurance: Codex-Gated Migration Testing for Banks

It turns a bank conversion spec into executable migration tests, maps every failure back to a requirement, lets Codex propose fixes, and produces an audit-ready evidence pack after approval.

## Commands

- `make setup`
- `make test`
- `make demo`
- `make dev`
- `make smoke`

`make demo` is fixture mode, zero secrets, no live model calls, no live Codex calls.

`make demo-live` is not implemented yet. Recorded Devpost video must use live mode later. Current scaffold is frontend-ready and fixture-backed.

## Where GPT-5.6 and Codex work

- GPT-5.6 will later extract requirements, generate adversarial records, and support root-cause reasoning.
- Codex will later inspect the repo, generate tests, propose patches, and apply approved patches.
- This scaffold intentionally uses frozen fixture outputs only.
- Fixture mode is for frontend development, CI, determinism tests, and judge-runnable offline demo.
