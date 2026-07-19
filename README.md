# Release Assurance: Codex-Gated Migration Testing for Banks

Release Assurance turns the canonical banking conversion specification into schema-validated requirements, runs deterministic migration checks, maps failures back to requirements, presents a Codex patch proposal for human review, and produces downloadable audit evidence after the approval-gated rerun.

## Setup and commands

The Make targets work on macOS and Linux, and on Windows when GNU Make is
installed. Windows users without GNU Make can run the Bun commands shown below.

```bash
make setup
make test
make demo
make demo-live
make dev
make smoke
```

### Local development

One command starts the API on `127.0.0.1:9001` and the web app on `127.0.0.1:9000` in the same terminal.

On macOS or Linux, activate the virtual environment and run from the repository root:

```bash
source .venv/bin/activate
make dev
```

On Windows PowerShell, activate the virtual environment and run the cross-platform Bun command:

```powershell
.\.venv\Scripts\Activate.ps1
cd frontend
bun dev
```

Press `Ctrl-C` once to stop both processes.

### Deterministic fixture demo

`make demo` runs the deterministic fixture mode with zero secrets, zero live GPT-5.6 calls, and zero live Codex calls. This is the supported offline, clean-laptop, and judge-runnable path. The fixture replay uses the frozen canonical banking inputs and model outputs while preserving the same persisted API, approval, rerun, and evidence flow.

### Live recording runtime

`make demo-live` starts the backend and frontend for the live recording path. It requires:

- a nonempty `OPENAI_API_KEY`
- an API model available to the key, configured with `RELEASE_ASSURANCE_GPT_MODEL` (the example uses `gpt-5.6-sol`)
- an installed and authenticated local Codex CLI (or an executable selected with `RELEASE_ASSURANCE_CODEX_EXECUTABLE`)

Starting `make demo-live` performs prerequisite checks, including `codex --version`, but makes no paid model call. Open `http://127.0.0.1:9000` for the normal manual UI, where the paid live flow begins only when **Run Live GPT + Codex** is clicked.

For a directed recording, open `http://127.0.0.1:9000/?director=1`. This explicit query parameter enables the Space-key director; pressing Space begins runtime speech generation and the automated live flow. Without `?director=1`, Space has no demo-director behavior.

On Windows PowerShell, start the same one-terminal live runtime from the repository root:

```powershell
$env:OPENAI_API_KEY = "<your-openai-api-key>"
bun run scripts/demo-live.ts
```

The launcher resolves npm-installed Codex command shims on Windows and invokes
`codex.cmd` through the Windows command processor automatically.

The live GPT plus Codex implementation exists, but it has not completed a supervised paid-call rehearsal in the target recording environment.

In the live flow:

1. Live GPT-5.6 extracts requirements from the canonical implementation document and validates the resulting control manifest against the frozen contracts.
2. Deterministic migration checks run against the canonical banking records.
3. Live Codex proposes a read-only patch diff.
4. A human must inspect the proposed diff, enter an approval note, and approve it before a rerun can occur.
5. The approved patch is applied only to a disposable workspace, where the deterministic acceptance checks run and the resulting evidence pack becomes downloadable.

Only defined model-shaped objects, including the control manifest and patch proposal, are schema validated. Other outputs, reports, and logs are not universally schema validated.

In both fixture and live approved-patch verification, the patched Python executes with the user's normal machine permissions. The disposable workspace protects the repository from modification, but it is **not a security sandbox**. Human inspection of the complete diff is the real execution-control boundary.

## Media attribution

The demo uses [Background Music Soft Calm](https://pixabay.com/music/upbeat-background-music-soft-calm-335280/) by INPLUSMUSIC, sourced from Pixabay and used under the [Pixabay Content License](https://pixabay.com/service/license-summary/).

## Scope and limitations

The deterministic acceptance verifier is specifically designed for the canonical banking demo fixture; it is not a general migration-verification engine. Browser actions use only the canonical repository input paths, and dropped files select the deterministic fixture replay rather than uploading their contents. Fixture mode remains the reproducible fallback for CI, clean laptops, and judges without live credentials.
