# Release Assurance: Codex-Gated Migration Testing for Banks

Release Assurance turns the canonical banking conversion specification into schema-validated requirements, runs deterministic migration checks, maps failures back to requirements, presents a Codex patch proposal for human review, and produces downloadable audit evidence after the approval-gated rerun.

## Setup and commands

```bash
make setup
make test
make demo
make demo-live
make dev
make smoke
```

### Deterministic fixture demo

`make demo` runs the deterministic fixture mode with zero secrets, zero live GPT-5.6 calls, and zero live Codex calls. This is the supported offline, clean-laptop, and judge-runnable path. The fixture replay uses the frozen canonical banking inputs and model outputs while preserving the same persisted API, approval, rerun, and evidence flow.

### Live recording runtime

`make demo-live` starts the backend and frontend for the live recording path. It requires:

- a nonempty `OPENAI_API_KEY`
- an installed and authenticated local Codex CLI (or an executable selected with `RELEASE_ASSURANCE_CODEX_EXECUTABLE`)

Starting `make demo-live` performs prerequisite checks, including `codex --version`, but makes no paid model call. The paid live flow begins only when **Run Live GPT + Codex** is clicked in the browser.

The live GPT plus Codex implementation exists, but it has not completed a supervised paid-call rehearsal in the target recording environment.

In the live flow:

1. Live GPT-5.6 extracts requirements from the canonical implementation document and validates the resulting control manifest against the frozen contracts.
2. Deterministic migration checks run against the canonical banking records.
3. Live Codex proposes a read-only patch diff.
4. A human must inspect the proposed diff, enter an approval note, and approve it before a rerun can occur.
5. The approved patch is applied only to a disposable workspace, where the deterministic acceptance checks run and the resulting evidence pack becomes downloadable.

Only defined model-shaped objects, including the control manifest and patch proposal, are schema validated. Other outputs, reports, and logs are not universally schema validated.

In both fixture and live approved-patch verification, the patched Python executes with the user's normal machine permissions. The disposable workspace protects the repository from modification, but it is **not a security sandbox**. Human inspection of the complete diff is the real execution-control boundary.

## Scope and limitations

The deterministic acceptance verifier is specifically designed for the canonical banking demo fixture; it is not a general migration-verification engine. Browser actions use only the canonical repository input paths, and dropped files select the deterministic fixture replay rather than uploading their contents. Fixture mode remains the reproducible fallback for CI, clean laptops, and judges without live credentials.
