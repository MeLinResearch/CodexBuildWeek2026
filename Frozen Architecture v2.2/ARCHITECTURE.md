# Release Assurance: Codex-Gated Migration Testing for Banks

## ARCHITECTURE.md — v2.2 FROZEN FINAL (2026-07-12)

**One-liner:** It turns a bank conversion spec into executable migration tests, maps every failure back to a requirement, lets Codex propose fixes, and produces an audit-ready evidence pack after approval.

**Governing principle:** deterministic core, LLMs at the edges. Every model output validates against a JSON Schema in `contracts/` before entering the pipeline. No raw model text ever touches financial records. The repo structure itself demonstrates this thesis.

**This document is the source of truth for all Codex tasks. Codex must read it and `contracts/` before any edit, and must never invent field names, state names, API routes, or schema properties.**

---

## 1. The demo loop (everything else is supporting structure)

```
implementation doc → requirements manifest → generated tests
→ failed migration records → traceability matrix
→ Codex proposes fix → human approval → rerun → green evidence report
```

Nothing gets built that doesn't serve this loop. Cut order if behind: PDF (HTML is primary) → adversarial generator (planted fixtures are primary) → root-cause agent (degrades to static rule→defect mapping) → Codex Phase 4 (degrades to "proposal + controlled manual apply", honestly labeled). **Never cut:** traceability matrix, live defect→patch→rerun loop, evidence HTML.

---

## 2. Two demo modes (non-negotiable integrity rule)

| Command | Behavior |
|---|---|
| `make demo` | offline, deterministic, fixture-backed model clients, zero secrets, judge-runnable on a clean laptop |
| `make demo-live` | real GPT-5.6 + real Codex, requires `OPENAI_API_KEY`, **THE ONLY PATH USED IN THE RECORDED DEVPOST VIDEO** |

Fixtures are the reproducibility layer. Live Codex is the Devpost proof. The integrity failure is not having fixtures; it is passing fixture output off as live. Therefore mode is labeled everywhere:

- UI "Model actions" panel shows: `Codex mode: LIVE|FIXTURE`, task id, sandbox policy, GPT-5.6 call counts, "all outputs schema-validated"
- Evidence pack embeds the mode in provenance
- `FixtureLLMClient` / `FixtureCodexClient` outputs are frozen files in `fixtures/model_outputs/`, used for: frontend dev, CI, determinism tests, offline judge demo. Nothing else.

The fixture boundary covers **ALL** model calls (requirements agent, adversarial gen, root cause via `llm/client.py`; test/patch work via `codex/client.py`). `make demo` must never require a key at any pipeline stage.

---

## 3. Repo layout (shallow — directories created as modules land)

```
release-assurance/
├── ARCHITECTURE.md
├── README.md              # setup, both demo paths, arch diagram, model-usage
│                           # narrative ("Where GPT-5.6 and Codex work"), limitations
├── Makefile                # demo | demo-live | test | dev
├── .env.example             # OPENAI_API_KEY (GPT-5.6). make demo needs NO env;
│                           # make demo-live may additionally require Codex
│                           # CLI/SDK auth — documented after the Day 0/1 spike
├── .python-version          # pinned; exact-ish dep ranges in pyproject.toml;
│                           # frontend lockfile committed
├── .github/workflows/ci.yml # runs: make test && make demo — the
│                           # judge-clones-repo scenario, verified on every push.
│                           # make demo is HEADLESS when CI=1 (prints URL, never
│                           # opens a browser; auto-open lives only in make dev).
│                           # make smoke = clean-clone path: deps + tests + demo
├── contracts/               # frozen after Day 0 — see §4
├── backend/
├── frontend/
├── reconcile/                # existing engine, vendored. reconcile/README.md
│                           # MUST state: pre-existing code, original repo
│                           # link, imported commit SHA, and what changed
│                           # during Build Week (rules-compliance record)
├── fixtures/
└── scripts/                 # demo.sh, smoke.sh
```

Each top-level directory gets a 3-line README (purpose, status, owner) until populated. Deeper structure (below) is created **only** when the module is built — no empty-tree architecture theater.

### Backend target structure as modules land:

```
backend/
├── pyproject.toml
├── app/
│   ├── main.py          # FastAPI
│   ├── config.py        # env, model names, paths. Model names and Codex
│   │                    # command strings live ONLY here — no module may
│   │                    # hardcode "gpt-5.6", "codex exec", or model IDs
│   ├── routers/         # runs.py, approvals.py, evidence.py
│   ├── pipeline/        # orchestrator.py, requirements_agent.py,
│   │                    # adversarial_gen.py (stretch), root_cause.py,
│   │                    # evidence_pack.py
│   ├── codex/           # client.py (interface), live_client.py,
│   │                    # fixture_client.py, phases.py, sandbox.py
│   ├── llm/             # client.py (interface), live_client.py,
│   │                    # fixture_client.py, validate.py
│   └── store/           # schema.sql, db.py, models.py
└── tests/                # test_contracts.py, test_pipeline.py,
                          # test_determinism.py, test_llm_validate.py
```

### Frontend:

```
frontend/
├── package.json         # React + Vite
└── src/
    ├── api/client.ts     # HANDWRITTEN typed client (no generator)
    ├── screens/          # TraceabilityMatrix, RecordDrilldown,
    │                    # ApprovalGate, RunComparison
    ├── components/       # ModelActionsPanel, StatusChip
    └── mocks/            # fixture JSON conforming to contracts/
```

---

## 4. Contracts (Day 0, frozen)

Files in `contracts/`:

```
provenance.schema.json        # shared $ref — defined ONCE
run_request.schema.json       # POST /api/runs body
run_status.schema.json        # includes the frozen state enum
control_manifest.schema.json
traceability_row.schema.json
failed_record.schema.json
mapping_proposal.schema.json
patch_proposal.schema.json
summary_stats.schema.json
VERSION
```

Every major object embeds the provenance block via `$ref`:

```json
{
  "schema_version": "2026-07-12.1",
  "run_id": "RUN-...",
  "created_at": "...",
  "source_artifact_ids": ["ART-001", "ART-002"],
  "producer": "gpt-5.6 | codex | deterministic | fixture",
  "mode": "live | fixture",
  "client": "LiveLLMClient | FixtureLLMClient | LiveCodexClient | FixtureCodexClient | none",
  "validation_status": "not_required | quarantined | validated | rejected"
}
```

Schema strictness rules: every schema uses JSON Schema Draft 2020-12, includes `$schema` and `$id`, sets `additionalProperties: false` unless explicitly justified in a comment, and enforces stable ID regex patterns for `RUN-`/`REQ-`/`TEST-`/`FAIL-`/`PATCH-`/`ART-` identifiers.

**Stable ID scheme** (joins across the whole system, Codex must use these): `RUN-###`, `REQ-###`, `TEST-###`, `FAIL-###`, `PATCH-###`, `ART-###`.

### Traceability row (core shape):

```json
{
  "requirement_id": "REQ-003",
  "test_id": "TEST-003",
  "failure_ids": ["FAIL-017"],
  "patch_id": "PATCH-002",
  "row_status": "failed",
  "evidence_refs": ["ART-009"],
  "provenance": { "...": "..." }
}
```

`row_status` enum (row-level, lowercase — **NEVER** reuse run-level states): `pending | passed | failed | patch_pending | patch_approved | rerun_passed`

### Failed record (core shape):

```json
{
  "failure_id": "FAIL-017",
  "record_id": "TXN-000184",
  "requirement_id": "REQ-003",
  "field": "account_id",
  "expected": "preserve leading zeros",
  "actual": "12345",
  "severity": "blocking",
  "record_hash": "sha256:..."
}
```

---

## 5. Run state machine (FROZEN ENUM — no additions, no renames)

```
CREATED → INGESTED → MANIFEST_READY → TESTS_GENERATED → EXECUTED → TRIAGED
TRIAGED → EVIDENCE_READY                 (zero failures: clean run)
TRIAGED → PATCH_PENDING                  (failures exist)
PATCH_PENDING → PATCH_APPROVED → RERUNNING
PATCH_PENDING → PATCH_REJECTED → TRIAGED (rejected patches never rerun)
RERUNNING → EVIDENCE_READY               (green rerun)
RERUNNING → TRIAGED                      (rerun still has failures → next cycle;
                                           prevents a false green after a bad patch)
EVIDENCE_READY → DONE
FAILED (terminal, reachable from any state on system error)
```

Every transition persisted to SQLite with timestamp and actor. The audit trail **IS** the product; the state machine produces it for free and makes the demo crash-resumable.

---

## 6. API surface (final — `/api` prefix everywhere)

```
POST /api/runs → run_id
  body per run_request.schema.json — artifact IDs do NOT pre-exist;
  ingestion creates ART-### records:
    fixture: { "mode": "fixture", "fixture_set": "bank_migration_demo_v1" }
    live:    { "mode": "live",
               "implementation_doc_path": "fixtures/implementation_doc.md",
               "source_data_path": "fixtures/source_data/accounts.csv",
               "target_schema_path": "fixtures/schemas/target_schema.json" }

GET  /api/runs/{run_id}                        → run_status
GET  /api/runs/{run_id}/matrix                  → traceability_row[]
GET  /api/runs/{run_id}/failures/{failure_id}   → failed_record
GET  /api/runs/{run_id}/patches                 → patch_proposal[] (ApprovalGate list)
GET  /api/patches/{patch_id}                    → patch_proposal (ApprovalGate detail)
POST /api/patches/{patch_id}/approve            body: { "actor": "demo_user", "note": "optional" }
POST /api/patches/{patch_id}/reject             body: { "actor": "demo_user", "note": "optional" }
POST /api/runs/{run_id}/rerun                   precondition: run state == PATCH_APPROVED,
                                                 else 409
GET  /api/runs/{run_id}/evidence                → HTML (PDF stretch)
```

---

## 7. SQLite schema (defined before Codex writes store code)

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE runs (
  run_id TEXT PRIMARY KEY,
  state TEXT NOT NULL CHECK (state IN (
    'CREATED','INGESTED','MANIFEST_READY','TESTS_GENERATED','EXECUTED',
    'TRIAGED','PATCH_PENDING','PATCH_APPROVED','PATCH_REJECTED',
    'RERUNNING','EVIDENCE_READY','DONE','FAILED'
  )),
  mode TEXT NOT NULL CHECK (mode IN ('live','fixture')),
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE state_transitions (
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  from_state TEXT CHECK (
    from_state IS NULL OR from_state IN (
      'CREATED','INGESTED','MANIFEST_READY','TESTS_GENERATED','EXECUTED',
      'TRIAGED','PATCH_PENDING','PATCH_APPROVED','PATCH_REJECTED',
      'RERUNNING','EVIDENCE_READY','DONE','FAILED'
    )
  ),
  to_state TEXT NOT NULL CHECK (to_state IN (
    'CREATED','INGESTED','MANIFEST_READY','TESTS_GENERATED','EXECUTED',
    'TRIAGED','PATCH_PENDING','PATCH_APPROVED','PATCH_REJECTED',
    'RERUNNING','EVIDENCE_READY','DONE','FAILED'
  )),
  actor TEXT NOT NULL,
  at TEXT NOT NULL
);

CREATE TABLE requirements (
  requirement_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  rule_type TEXT NOT NULL CHECK (rule_type IN (
    'field_validation','balancing_rule','exception_handling','mapping_rule','tolerance_rule'
  )),
  tolerance TEXT,
  provenance TEXT NOT NULL CHECK (json_valid(provenance))
);

CREATE TABLE tests (
  test_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  requirement_id TEXT NOT NULL REFERENCES requirements(requirement_id),
  name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','passed','failed','skipped')),
  output_ref TEXT,
  provenance TEXT NOT NULL CHECK (json_valid(provenance))
);

CREATE TABLE failures (
  failure_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  requirement_id TEXT NOT NULL REFERENCES requirements(requirement_id),
  test_id TEXT NOT NULL REFERENCES tests(test_id),
  record_id TEXT NOT NULL,
  field TEXT,
  expected TEXT NOT NULL,
  actual TEXT,
  severity TEXT NOT NULL CHECK (severity IN ('blocking','warning','info')),
  record_hash TEXT,
  provenance TEXT NOT NULL CHECK (json_valid(provenance))
);

CREATE TABLE patches (
  patch_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  failure_ids TEXT NOT NULL CHECK (json_valid(failure_ids)),
  diff TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','approved','rejected','applied','apply_failed')),
  approved_by TEXT,
  approved_at TEXT,
  applied_at TEXT,
  provenance TEXT NOT NULL CHECK (json_valid(provenance))
);

CREATE TABLE artifacts (
  artifact_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(run_id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN (
    'input','raw_model_output','validated_model_output','test_output',
    'patch_diff','evidence_html','evidence_pdf','log'
  )),
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  producer TEXT NOT NULL CHECK (producer IN ('gpt-5.6','codex','deterministic','fixture')),
  mode TEXT NOT NULL CHECK (mode IN ('live','fixture')),
  client TEXT NOT NULL,
  validation_status TEXT NOT NULL CHECK (validation_status IN (
    'not_required','quarantined','validated','rejected'
  )),
  created_at TEXT NOT NULL
);

CREATE INDEX idx_requirements_run_id ON requirements(run_id);
CREATE INDEX idx_tests_run_id ON tests(run_id);
CREATE INDEX idx_failures_run_id ON failures(run_id);
CREATE INDEX idx_patches_run_id ON patches(run_id);
CREATE INDEX idx_artifacts_run_id ON artifacts(run_id);
```

`artifacts.run_id` is intentionally nullable: input artifacts are seeded by `scripts/demo.sh` BEFORE any run exists.

**FROZEN VALUE ENUMS** (propagate to contracts, do not drift):
- test status: `pending|passed|failed|skipped`
- failure severity: `blocking|warning|info`
- patch status: `pending|approved|rejected|applied|apply_failed`
- artifact validation_status: `not_required|quarantined|validated|rejected`

---

## 8. Codex integration

Interface (the **ONLY** files that talk to Codex live in `backend/app/codex/`):

```python
class CodexClient(Protocol):
    def inspect_and_test(
        self, repo_path: Path, manifest: ControlManifest,
        sandbox_policy: SandboxPolicy,
    ) -> TestArtifacts: ...

    def propose_patch(
        self, repo_path: Path, manifest: ControlManifest,
        failures: list[FailedRecord], test_artifacts: TestArtifacts,
        sandbox_policy: SandboxPolicy,
    ) -> PatchProposal: ...

    def apply_approved_patch(
        self, repo_path: Path, patch: PatchProposal,
        sandbox_policy: SandboxPolicy,
    ) -> ApplyResult: ...
```

All context is passed explicitly — the client never queries SQLite itself. No hidden coupling; fixture and live implementations stay swappable.

Implementations: `LiveCodexClient` (`codex exec` / SDK, persistent thread, sandbox policy enforced in `sandbox.py`) and `FixtureCodexClient` (frozen artifacts, labeled).

**Four phases, four separate milestones:**
1. **Phase 1:** inspect repo, generate tests, execute, report — **SUBMITTABLE FLOOR**
2. **Phase 2:** propose patches as diffs (read-only)
3. **Phase 3:** approval gate — patch persists PENDING; endpoint flips state; approval must show diff, affected requirement, and failing test
4. **Phase 4:** apply approved patch (workspace-write), trigger rerun

### Day 0/1 operational spike (GATE — backend work depending on Codex waits)

The spike must prove, in order:
1. `codex exec` runs non-interactively
2. read-only inspection can be forced
3. task context can be resumed/persisted
4. structured output / artifact path capturable
5. can generate tests
6. can run tests
7. can propose a patch as a diff
8. can switch to workspace-write only after approval

1–6 pass → Phase 1 shippable. 7–8 fail → approval gate becomes "Codex proposal + controlled manual apply," described honestly in demo and README. Results recorded in `backend/app/codex/live_spike.md`.

### Patch safety (enforced in `sandbox.py` before any apply)

Approval does not mean "apply whatever diff Codex produced." Before apply:
- reject absolute paths and paths outside the repo
- reject edits to `contracts/`, `.env*`, secrets, lockfiles unless the task explicitly allows it
- reject binary patches and patches over a max size
- reject symlinks and symlink traversal; normalize paths BEFORE allow/deny checks; apply only from repo root
- reject file mode changes unless explicitly allowed
- run `git apply --check` before apply
- record pre-apply and post-apply tree hashes in the patch provenance
- redact secrets from Codex logs before storing them as artifacts
- apply in a disposable workspace first; run the affected tests there; only then mark PATCH applied and transition to RERUNNING

The product is literally approval-gated automation — the gate must be mechanical, not ceremonial.

---

## 9. Planted defects (`fixtures/planted_defects/` + `DEFECTS.md`)

Three defects, each a real bank-conversion defect class, each detected by a different mechanism, each a visually distinct matrix row:

1. **Leading-zero truncation** — account IDs int-coerced. Violates "preserve account identifiers verbatim." (field validation)
2. **Sign inversion on one transaction code** — global totals pass, branch-level fails. Violates "debits equal credits by branch." (balancing rule) — USE SMALL VISIBLE NUMBERS the matrix shows exactly: Branch 101 debits 1,250.00 / credits 1,200.00 / diff 50.00. Every number spoken in the video must match the screen.
3. **Silent date default** — unparseable dates coerced to 1900-01-01 instead of rejected. Violates "no silent value substitution." (exception-handling rule)

CI enforces detection: `test_pipeline.py::test_finds_all_planted_defects`.

---

## 10. Determinism test (non-negotiable)

`test_determinism.py`: same implementation doc + same input data + same planted defects + same FROZEN model fixture outputs + same contracts → byte-identical matrix JSON and byte-identical evidence HTML, run twice. No live model calls inside determinism tests, ever.

Determinism tests inject `FIXED_CLOCK=2026-07-12T00:00:00Z` and fixed sequential IDs (`RUN-001`, `ART-001`, ...) via config — timestamps and ID generation must be injectable, never called inline, or these tests will be flaky by construction.

All serialized JSON and evidence HTML sort rows by stable IDs (`requirement_id`, `test_id`, `failure_id`, `patch_id`, `artifact_id`). Database query order is never trusted without an explicit `ORDER BY`.

---

## 11. Frontend

Hero screen: traceability matrix, 7 columns — Requirement | Test | Status | Failures | Patch | Approval | Rerun (root cause and evidence live in RecordDrilldown to preserve legibility). Status chips keyed to the frozen state enum. `ModelActionsPanel` visible on every screen.

Frontend builds against `src/mocks/` from Day 0 and swaps to `/api` at Wednesday-evening integration — the swap is a data-source change, not a schema discovery.

---

## 12. Build order (Codex tasks follow this sequence)

1. `contracts/` (all schemas + VERSION)
2. contract tests (every schema validates; every JSON under `fixtures/` AND `frontend/src/mocks/` validates against `contracts/` — frontend mocks are never allowed to drift)
3. fixture JSON (matrix rows, failures, patches, model outputs)
4. `store/schema.sql` + `db.py`
5. state machine (orchestrator skeleton, transitions persisted)
6. mock pipeline (reads `fixtures/model_outputs/` JSON directly — does NOT depend on the `llm/` module from step 9; fixture clients later slot behind the same file-reading behavior) — this is `make demo` Day 1
7. API endpoints returning fixture data
8. frontend screens against mocks/API
9. `llm/` (interface, live client, fixture client, `validate.py`)
10. requirements agent
11. Codex Phase 1 (after spike gate passes)
12. approval gate (Phases 2–3)
13. rerun (Phase 4 or honest fallback)
14. evidence HTML, README hardening, model-usage narrative

`make demo` exists from step 6 onward and **MUST NEVER BREAK thereafter**.

---

## 13. Hard implementation invariants (Codex must never violate these)

- Fixture mode must never call live LLM or Codex clients.
- Live demo must never use fixture model outputs.
- All model outputs are stored as artifacts BEFORE validation.
- Only validated structured outputs enter pipeline tables.
- Raw model text is retained only as quarantined artifacts, never as pipeline state.
- Patch application always happens in a disposable workspace and passes tests before being marked applied.
- Determinism tests use fixed IDs and a fixed clock.
- Timestamps and ID generation are injectable dependencies, never inline calls.

---

## 14. Codex task rules (prepend to every task)

```
You are modifying the OpenAI Build Week hackathon repo.
Do not change contracts/ unless this task explicitly says to.
Do not change reconcile/ unless this task explicitly says to.
Do not invent field names, state names, API routes, or schema properties.
Read ARCHITECTURE.md and contracts/ before editing.
Implement only the requested module.
Add or update tests for the requested module.
Run the relevant tests.
Return: 1) files changed 2) tests run 3) remaining risks
```

Task sizing: one module per task ("Implement `backend/app/llm/validate.py` per ARCHITECTURE.md §2/§4; reject invalid outputs with structured `ValidationError`; add `backend/tests/test_llm_validate.py`") — never "build the backend."
