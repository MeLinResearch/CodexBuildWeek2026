# Release Assurance: Codex-Gated Migration Testing for Banks

Release Assurance catches silent banking migration defects before they ship. It turns a conversion specification into traceable requirements, runs deterministic checks, maps each failure to the requirement it violates, presents a bounded Codex patch proposal for human review, and produces an audit-ready evidence pack after the approval-gated rerun.

**Codex proposes. Humans approve. Auditors get receipts.**

## Judge quickstart

The supported judging path is deterministic fixture mode. It uses canonical synthetic banking data, requires zero secrets, and makes zero live GPT-5.6 or Codex calls while exercising the same persisted API, approval, rerun, and evidence flow shown in the submitted demo.

Requirements:

- Python 3.12 or newer
- Bun 1.3.x
- GNU Make on macOS, Linux, or Windows

From the repository root:

```bash
make setup
make test
make demo
```

`make test` runs the Python backend tests, frontend lint and tests, and the production frontend build. `make demo` runs the complete FastAPI fixture smoke path from failure through approval, rerun, a green traceability matrix, and evidence generation.

For the visual application:

```bash
make dev
```

Then open `http://127.0.0.1:9000`. The API runs on `127.0.0.1:9001`. Press `Ctrl-C` once to stop both processes.

CI runs `make setup`, `make test`, and `make demo` on Ubuntu, macOS, and Windows.

## What the product proves

Release Assurance implements a bounded operating model for AI in regulated workflows:

1. GPT-5.6 translates implementation prose into a schema-validated control manifest with provenance.
2. Deterministic checks decide whether the migrated records satisfy those requirements.
3. Every failure maps back to a stable requirement and evidence artifact.
4. Codex analyzes the failure and returns a narrowly scoped, reviewable patch proposal.
5. A human must inspect the complete diff, enter a decision note, and explicitly approve it.
6. The approved patch is verified in a disposable workspace.
7. The evidence pack preserves provenance, traceability, the decision record, verification results, and the state-transition audit trail.

Models interpret and propose. Deterministic systems verify. Humans authorize consequential actions.

## How GPT-5.6 and Codex were used

### During development

GPT-5.6 was used as a planning, requirements-analysis, and review partner throughout Build Week. It helped inspect repository state, translate human product and architecture decisions into bounded implementation tasks, review actual patches and CI evidence, diagnose cross-platform failures, and keep the fixture and live claims explicit.

Codex executed narrowly scoped engineering tasks across the repository. Its work included backend and frontend implementation slices, schema and patch-safety validation, test generation and refinement, Windows and browser-automation debugging, cross-platform demo tooling, and final workflow hardening. The human team retained the product, architecture, scope, and approval decisions.

Representative evidence:

- [Codex feedback session](https://chatgpt.com/s/cd_6a5e9a0b4798819183a1ebf3d0250d84)
- [PR #27: isolated live GPT-5.6 and Codex proposal boundaries](https://github.com/MeLinResearch/CodexBuildWeek2026/pull/27)
- [Dated pull-request history](https://github.com/MeLinResearch/CodexBuildWeek2026/pulls?q=is%3Apr)

### Inside Release Assurance

The model boundaries are deliberately narrow:

- GPT-5.6 may extract structured requirements, but it cannot determine whether the migration passed.
- Codex may propose a patch, but it cannot approve or silently apply its own work.
- Model-shaped outputs are validated before entering deterministic processing.
- Raw model text is quarantined.
- Patch scope and applicability are checked before the proposal reaches the reviewer.
- Human approval remains mandatory before verification.

## Deterministic fixture mode

`make demo` is the supported offline, clean-laptop, and judge-runnable path. The fixture replay uses frozen canonical banking inputs and model-shaped outputs while preserving the real application workflow:

- requirements and provenance
- deterministic failures
- traceability matrix
- complete patch diff
- reviewer note and approval
- disposable rerun
- green verification state
- downloadable evidence pack

Fixture artifacts are labeled as fixture evidence and are never represented as live model output.

## Optional credentialed live runtime

`make demo-live` starts the optional credentialed GPT-5.6 and Codex path. It requires:

- a nonempty `OPENAI_API_KEY`
- an API model available to the key, configured with `RELEASE_ASSURANCE_GPT_MODEL`
- an installed and authenticated Codex CLI, or an executable selected with `RELEASE_ASSURANCE_CODEX_EXECUTABLE`

Starting `make demo-live` performs prerequisite checks but makes no paid model call. The paid flow begins only when **Run Live GPT + Codex** is clicked in the application.

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY = "<your-openai-api-key>"
bun run scripts/demo-live.ts
```

The submitted video and supported judging path use deterministic fixture mode. The optional live adapters demonstrate the isolated GPT-5.6 extraction and read-only Codex proposal boundaries without making live credentials a judging requirement.

## Windows without GNU Make

Activate the virtual environment and install the dependencies from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e "backend[dev]"
cd frontend
bun install --frozen-lockfile
bun dev
```

For the equivalent test path, run the backend tests from the repository root, then the frontend lint, tests, and build:

```powershell
python -m pytest backend/tests
cd frontend
bun lint
bun test
bun run build
```

## Build Week scope and provenance

The base deterministic migration engine in `reconcile/` is pre-existing work originally developed in [MeLinResearch/Reconcile](https://github.com/MeLinResearch/Reconcile). It was imported under the MIT License from commit `b280ed49388791f3cae7fa2fc88144c2c706bd9d` and was not created during OpenAI Build Week. Detailed provenance and the exact vendoring changes are documented in [`reconcile/README.md`](reconcile/README.md).

The work created during the July 13 to July 21, 2026 submission period is Release Assurance around that engine:

- frozen contracts and canonical synthetic fixtures
- the GPT-5.6 requirement-extraction boundary
- deterministic banking controls and failure evidence
- the Codex patch-proposal and patch-safety boundary
- the FastAPI workflow, state machine, persistence, and API
- the React traceability, diff-review, approval, rerun, and evidence experience
- disposable verification and evidence generation
- cross-platform CI, testing, and demo tooling

Initial project scaffolding used Claude/Fable and is not represented as Codex work. The linked Codex session, Codex-linked pull requests, and dated commit history distinguish the later GPT-5.6 and Codex contributions.

## Safety boundaries

Only defined model-shaped objects, including the control manifest and patch proposal, are schema validated. Reports and logs are not universally schema validated.

In both fixture and live approved-patch verification, the patched Python executes with the user's normal machine permissions. The disposable workspace protects the repository from modification, but it is not a security sandbox. Human inspection of the complete diff is the execution-control boundary.

The deterministic acceptance verifier is specifically designed for the canonical banking fixture. It is not represented as a general-purpose migration-verification engine. Browser actions use only canonical repository input paths, and dropped files select the deterministic fixture replay rather than uploading arbitrary contents.

## Media attribution

The demo uses [Background Music Soft Calm](https://pixabay.com/music/upbeat-background-music-soft-calm-335280/) by INPLUSMUSIC, sourced from Pixabay and used under the [Pixabay Content License](https://pixabay.com/service/license-summary/).

## License

Release Assurance is available under the [MIT License](LICENSE).
