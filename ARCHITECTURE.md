ARCHITECTURE.md — v2.2 FROZEN FINAL (2026-07-12)

Project title:
Release Assurance: Codex-Gated Migration Testing for Banks

One-liner:
It turns a bank conversion spec into executable migration tests, maps every failure back to a requirement, lets Codex propose fixes, and produces an audit-ready evidence pack after approval.

Governing principle:
Deterministic core, LLMs at the edges. Every model output validates against a JSON Schema in contracts/ before entering the pipeline. No raw model text ever touches financial records. The repo structure itself demonstrates this thesis.

This document is the source of truth for all Codex tasks. Codex must read it and contracts/ before any edit, and must never invent field names, state names, API routes, or schema properties.

1. The demo loop (everything is in a supporting illustration)

A fixture-only demo shows the end-to-end handoff surface:

1. A bank conversion implementation document is treated as the requirements source.
2. The deterministic scaffold exposes frozen contracts, fixture API responses, fixture frontend data, and a fixture evidence pack.
3. Requirements, generated tests, failures, patches, approvals, reruns, and evidence are connected through stable IDs.
4. The frontend engineer can wire screens against the frozen API without waiting for live LLM, Codex, database, or pipeline work.

2. Two demo modes: from compliance integrity risk

Mode A — fixture mode:
- Fully deterministic.
- No live LLM calls.
- No live Codex calls.
- No browser automation required for the CLI demo.
- No database persistence.
- Used by CI, smoke tests, screenshots, and frontend handoff.

Mode B — future live mode:
- May use LLM and Codex clients only after their outputs validate against contracts/.
- Must preserve the same public API surface unless a new frozen architecture version changes it.
- Must keep all model outputs quarantined until schema validation succeeds.
- Must keep approval gates between proposed patches and applied changes.

3. Repo layout (frozen — directories created or used in build)

```text
CodexBuildWeek2026/
  ARCHITECTURE.md
  README.md
  Makefile
  .env.example
  .gitignore
  contracts/
    VERSION
    control_manifest.schema.json
    failed_record.schema.json
    mapping_proposal.schema.json
    patch_proposal.schema.json
    provenance.schema.json
    run_request.schema.json
    run_status.schema.json
    summary_stats.schema.json
    traceability_row.schema.json
  fixtures/
    implementation_doc.md
    api/
      failed_record_FAIL-001.fixture.json
      failed_record_FAIL-002.fixture.json
      failed_record_FAIL-003.fixture.json
      patch_PATCH-001.fixture.json
      run_status.fixture.json
      summary_stats.fixture.json
      traceability_matrix.fixture.json
  backend/
    pyproject.toml
    app/
      main.py
      config.py
      fixture_loader.py
      routers/
        approvals.py
        evidence.py
        runs.py
    tests/
      test_api_contracts.py
      test_no_fake_dependencies.py
  frontend/
    package.json
    package-lock.json
    index.html
    vite.config.ts
    tsconfig.json
    tsconfig.app.json
    tsconfig.node.json
    src/
      vite-env.d.ts
      api/client.ts
      mocks/
      components/
      screens/
  reconcile/
  scripts/
    demo.sh
    smoke.sh
```

4. Contracts (top-down)

The frozen contract set is authoritative. JSON Schema files under contracts/ define every accepted field, enum, ID pattern, and required property. No implementation may add fields by convenience or accept raw model output outside those schemas.

Contract version:

```text
contracts/VERSION = 2.2
```

Required schemas:

```text
control_manifest.schema.json
failed_record.schema.json
mapping_proposal.schema.json
patch_proposal.schema.json
provenance.schema.json
run_request.schema.json
run_status.schema.json
summary_stats.schema.json
traceability_row.schema.json
```

The schema version carried in provenance-bearing payloads is:

```text
2026-07-12.1
```

5. Provenance contract

Every generated or fixture artifact that enters the pipeline includes provenance. Provenance records the producer, client, mode, source artifacts, validation status, and run ID.

Allowed provenance clients:

```text
LiveLLMClient
FixtureLLMClient
LiveCodexClient
FixtureCodexClient
none
```

Allowed producers:

```text
gpt-5.6
codex
deterministic
fixture
```

Allowed modes:

```text
live
fixture
```

Allowed validation statuses:

```text
not_required
quarantined
validated
rejected
```

6. Data state machine (frozen enums — no new states, no renamed states)

Allowed run states are exactly:

```text
CREATED
INGESTED
MANIFEST_READY
TESTS_GENERATED
EXECUTED
TRIAGED
PATCH_PENDING
PATCH_APPROVED
PATCH_REJECTED
RERUNNING
EVIDENCE_READY
DONE
FAILED
```

Allowed traceability row statuses are exactly:

```text
pending
passed
failed
patch_pending
patch_approved
rerun_passed
```

Allowed patch statuses are exactly:

```text
pending
approved
rejected
applied
apply_failed
```

Allowed failure severities are exactly:

```text
blocking
warning
info
```

7. Risk anchors in fixture data

The fixture scenario demonstrates three compliance-relevant migration risks:

```text
REQ-001 / TEST-001 / FAIL-001: preserve account identifiers verbatim, including leading zeroes.
REQ-002 / TEST-002 / FAIL-002: debits and credits must balance by branch.
REQ-003 / TEST-003 / FAIL-003: unparseable dates must be rejected, not silently substituted.
```

The frozen fixture run is:

```text
RUN-001
PATCH-001
```

8. API surface (frozen — no additions)

Allowed API routes are exactly:

```text
POST /api/runs
GET /api/runs/{run_id}
GET /api/runs/{run_id}/matrix
GET /api/runs/{run_id}/failures/{failure_id}
GET /api/runs/{run_id}/patches
GET /api/patches/{patch_id}
POST /api/patches/{patch_id}/approve
POST /api/patches/{patch_id}/reject
POST /api/runs/{run_id}/rerun
GET /api/runs/{run_id}/evidence
```

There is no `/api/runs/{run_id}/summary` route in v2.2. Summary statistics may be used as local mock UI data only until a later frozen architecture explicitly adds a route.

9. Model and Codex client boundaries

Live model calls are intentionally out of scope for this scaffold. Future work may add clients only behind explicit interfaces that preserve these constraints:

- Raw model text is quarantined.
- Quarantined output is validated against contracts/ before use.
- Invalid output is rejected and never enters the deterministic core.
- Codex proposals are patch proposals, not automatically applied changes.
- Human approval is required before any patch state advances to approved/applied.

10. Determinism and non-negotiables

The scaffold must remain deterministic and CI-safe:

- No OPENAI_API_KEY is required.
- No live LLM calls are required.
- No live Codex calls are required.
- No server or browser is required for the fixture demo.
- No database persistence is required.
- Fixture semantics must not change during cleanup tasks.
- Fake dependency stubs must not be committed.
- Toolchain checks must use real package managers and real dependencies.

11. Backend

The backend is a FastAPI fixture API. It serves frozen fixture payloads and validates enough request shape to support the frozen surface. It must depend on real installed packages, not repository-local stubs.

Backend package metadata lives in backend/pyproject.toml. Development installation is:

```sh
python -m pip install -e "backend[dev]"
```

Backend tests are run with:

```sh
python -m pytest backend/tests
```

12. Build order (Codex tasks follow this sequence)

1. Read ARCHITECTURE.md.
2. Read contracts/.
3. Inspect fixtures/ without changing fixture semantics.
4. Verify no local fake dependency stubs shadow installed packages.
5. Install backend and frontend dependencies with the real toolchains.
6. Run backend tests.
7. Run frontend TypeScript/Vite build.
8. Run make setup, make test, CI=1 make demo, and make smoke.
9. Commit only deterministic scaffold and cleanup changes.
10. Do not add routes, schemas, IDs, enums, states, or fields outside this frozen document and contracts/.

13. Handoff implementation constraints (Codex must never violate these)

Codex must not:

- Add product features.
- Implement live LLM calls.
- Implement live Codex calls.
- Implement real database persistence.
- Implement the real pipeline.
- Change fixture semantics.
- Invent routes, schemas, IDs, enums, states, or API fields.
- Fake test success.
- Hand-write package-lock.json.
- Reintroduce fake dependency stubs.

14. Screens that future frontend work can safely build

The frontend can safely build against these fixture-backed surfaces:

- Model actions / run status panel.
- Traceability matrix.
- Failed record drilldown.
- Patch proposal and approval gate.
- Rerun comparison using local summary fixture data.
- Evidence pack link or preview.

15. Demo readiness contract

The canonical fixture demo command is:

```sh
CI=1 make demo
```

It must remain headless, require no servers, require no browser, require no API key, and print exactly:

```text
Fixture demo ready
```

16. Current task status

This repository is a fixture-backed scaffold, not a production pipeline. Its purpose is to preserve the frozen architecture, contracts, fixture semantics, and handoff-safe toolchain so subsequent frontend and backend work can proceed without re-litigating the API or data model.
