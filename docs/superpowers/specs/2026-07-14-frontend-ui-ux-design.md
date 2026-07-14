# Frontend UI/UX Design: Release Assurance

Date: 2026-07-14
Status: approved in brainstorming, pending final review
Scope: `frontend/` only. Backend, contracts, and fixtures are frozen (ARCHITECTURE.md v2.2).

## 1. Goal

Replace the scaffold frontend (four static sections stacked on one page) with a polished single-run workspace that tells the product story: spec to tests to failures to traceability to Codex patch to human approval to rerun to green evidence. The UI must be genuinely useful (clear hierarchy, self-explanatory failures, honest mode labeling), which also serves the Devpost video and judge walkthroughs.

Non-negotiable constraints inherited from ARCHITECTURE.md v2.2:

- Traceability matrix is the hero screen with exactly 7 columns: Requirement, Test, Status, Failures, Patch, Approval, Rerun.
- Status chips key to the frozen `row_status` and run-state enums. No new state names.
- ModelActionsPanel is visible on every screen: Codex mode LIVE or FIXTURE, task id, sandbox policy, GPT-5.6 call counts, "all outputs schema-validated".
- Frontend builds against `src/mocks/` and swaps to `/api` as a data-source change only (`USE_API` flag in the handwritten `api/client.ts`).
- Approval must show the diff, the affected requirement, and the failing test.
- Every number shown must match the fixture data exactly (spoken numbers in the video match the screen): expected `00012345` vs actual `12345`; Branch 101 debits `1,250.00`, credits `1,200.00`, difference `50.00`; silent date default `1900-01-01`.

## 2. Information architecture

A single-run workspace with three permanent zones.

**Top bar** (design-system title bar, sunken surface): gradient glyph mark + "Release Assurance" wordmark, run chip (mono, `RUN-001 · PATCH_PENDING`), mode badge (FIXTURE = warning style with pulsing dot, LIVE = success style), actor label, theme toggle.

**Pipeline rail** (left, ~240px, sidebar-nav style): the run state machine rendered as 8 navigable stops: Ingested, Manifest, Tests, Executed, Matrix, Approval, Rerun, Evidence. Each stop: 7px stage dot (done = indigo, current = amber with `q-pulse` halo, todo = faint), 13px label, right-aligned mono count ("3 fail", "1 pending"). Completed stops navigate to that stage's view; future stops are disabled. Active stop = white card with hairline border and shadow. `FAILED` renders as a full-width danger banner above the content area, not a rail stop. ModelActionsPanel is a compact card pinned to the rail bottom (satisfies "visible on every screen" without eating content width).

**Stage content area**, mapped run-state to view:

| Run state reached | View |
|---|---|
| CREATED through EXECUTED | Run progress (live checklist, artifact chips appearing) |
| TRIAGED | Traceability matrix (default landing view from here on) |
| PATCH_PENDING | Approval gate |
| PATCH_APPROVED / RERUNNING | Matrix in rerun mode (rows flip live) |
| EVIDENCE_READY / DONE | Run comparison + evidence link |
| FAILED | Danger banner + last transition details over the last good view |

Matrix-as-hero rule: whenever the run is TRIAGED or later, the matrix is the default view and always one click away (first enabled rail stop). Record drilldown is not a stage: it is a right-side panel (~400px) sliding over any view.

Empty state (no run): centered "Start run" card, mode selector with fixture preselected, primary CTA creates the run via `POST /api/runs`.

## 3. Screens

### 3.1 Traceability matrix (hero)

- 7 frozen columns. Requirement cells show the ID (mono) with the requirement text beneath in secondary color ("Preserve account identifiers verbatim").
- Status chips per frozen `row_status` enum: `pending` gray, `passed` green, `failed` danger, `patch_pending` warning, `patch_approved` indigo tint, `rerun_passed` green with a rerun glyph.
- Failure IDs are danger-colored links opening the drilldown panel. Patch IDs open the approval gate. Approval column shows a compact "Review" line button while pending, then the approval result with actor. Rerun column: "not started", spinner while RERUNNING, then pass/fail chip.
- Four stat tiles above the table (requirements, tests, failures, patches) with mono numbers; failures tile uses danger color when nonzero.
- Rerun mode: rows flip `failed` to `rerun_passed` with a 150ms stagger and a brief green background flash, then the rail's Evidence stop lights up.

### 3.2 Record drilldown (right panel)

Opens over any view (row click, failure link, or diff badge click). Contents, top to bottom:

- Header: failure ID (mono) + severity chip + close button.
- Plain-language meaning (one sentence, from a small frontend-owned map keyed by `requirement_id`, falling back to the record's `expected` text; `rule_type` is not exposed by the API).
- Where it was seen: data location chips (source file, `record_id`, `field`).
- Where the fix lands: `file:line` chips in indigo tint (derived from the patch diff hunks).
- Expected vs actual as a two-row mono comparison with changed characters highlighted.
- Requirement: ID + full text.
- Provenance block: producer, client, mode, validation status, schema version (dashed border card, mono).
- CTA: "Review PATCH-001".

Esc or ✕ closes. Focus is trapped while open.

### 3.3 Approval gate

The v4 mockup, verbatim:

- Eyebrow (mono): "STAGE 6 OF 8 · RUN-001". Title with gradient emphasis: "Approve the Codex patch". Subtitle states the count of blocking failures and that nothing is applied without approval.
- Failure evidence cards (one per failure): FAIL chip, short name, one-sentence meaning, Seen and Fix location chips, key numbers in mono, requirement link, "Open record" affordance.
- Cross-linking (decided): hover a card to outline its diff lines (and vice versa via the diff's FAIL badges); click to filter the diff to that failure's hunks (with a "Show full patch" reset pill) and open the drilldown panel.
- Files-changed strip: every file in the patch as a mono tab with +/- counts; each file renders its own diff section beneath.
- Diff rendered by `@pierre/diffs`: stacked by default with a split toggle, line numbers, word-level change highlighting, FAIL badges as line annotations. Dark diff surface in both themes.
- Approval bar: optional note input (recorded in the audit trail), Reject (line button, opens a dialog requiring a note, returns run to TRIAGED), Approve (indigo accent CTA, the single most important action per the design system). Hint line spells out the transition: PATCH_APPROVED then RERUNNING.

Note: the current fixture diff is a one-line comment change. The UI renders whatever the API returns; if we later want a more impressive demo diff, that is a fixtures change (backend-owned), not a frontend concern.

### 3.4 Run comparison (EVIDENCE_READY / DONE)

Before/after columns: initial run (3 failed, danger rows) vs rerun (all passed, success rows), one resolution line per failure (FAIL-001 fixed by PATCH-001, verified by TEST-001), and a prominent "Open evidence pack" button pointing at `GET /api/runs/{id}/evidence`.

### 3.5 Run progress (pre-TRIAGED)

Live checklist mirroring the rail: current activity line per stage ("Extracting requirements... 3 found"), artifact chips appearing as ART-IDs are created. Fixture mode steps through at ~400ms per stage for demo rhythm.

## 4. Visual system

Source of truth: `design-system.md` (repo root) with values confirmed against project-seo (`packages/web/src/index.css`). Linear/Vercel-style serious SaaS: calm, precise, editorial-but-technical.

- **Canvas and surfaces (light, default):** page `#fafaf9`, cards/inputs `#ffffff`, sunken bars `#f7f6f4`, chips `#f4f3ef`. Hairline borders `rgba(10,10,10,.06)` (rest) and `.08` (controls). Soft layered shadows, small radii (4 to 14px, pill 999px).
- **Dark theme (toggle):** warm near-black canvas `#0f0f0e`, surface `#161615`, sunken `#131312`, chips `#22221f`, text `#f0efed` / `#a8a8a4` / `#6b6a64`, borders `rgba(255,255,255,.07)` and `.11`. Accent text lifts to `#a5a3f7`; solid buttons keep `#4338ca`. Status colors brighten: success `#34d399`, warning `#fbbf24`, danger `#f87171`, each on low-alpha tinted backgrounds. Light is the default; the toggle lives in the top bar; preference persists in localStorage.
- **Accent:** indigo `#4338ca` (hover `#3730a3`, violet partner `#6d28d9` only in the glyph mark, tint `#ecebff`). One accent. Approve is the only accent button on screen.
- **Status mapping (frozen enums to design-system status tokens):** success `#047857` on `#ecfdf3` (dot `#10b981`) for passed/rerun_passed/validated/LIVE; warning `#b45309` on `#fef3c7` (dot `#f59e0b`, `q-pulse`) for patch_pending/FIXTURE/awaiting states; danger `#be3a1d` on `#fef2f0` for failed/blocking/rejected; gray on `#f4f3ef` for pending/not started.
- **Typography:** Geist (sans) + Geist Mono via `@fontsource-variable`. Headings max weight 500, tight tracking; emphasis via the dark-to-indigo gradient span (light) / off-white-to-`#a5a3f7` (dark) on 1 or 2 words. Mono strictly for functional chrome: eyebrow labels (10px, 600, uppercase, .08em), IDs, counts, locations, timestamps, state names. Never sentences. No serif, no italics (project-seo's Instrument Serif is deliberately not adopted).
- **Signature elements reused:** stage dots (7px, indigo done, amber attn pulse), citation-chip pattern for FAIL chips and fix locations, judge-pill pattern for status chips, sidebar nav active-card pattern for the rail.
- Diff surfaces stay dark in both themes (Pierre dark theme) as the intentional technical contrast.

## 5. Interaction, motion, states

- Transitions default `.15s`; nav/hover `.1s`. The only looping animation is the 2s `q-pulse` on the current stage dot and mode badge.
- Stage completion: dot fills indigo, count ticks in, next stage picks up the pulse. Fixture runs step ~400ms per stage.
- Rerun sequence: auto-switch to matrix, rows flip with 150ms stagger and green flash, Evidence stop lights, then run comparison becomes the default view. Calm: color and sequence carry the drama, no confetti.
- Approve: button spinner, top-bar state chip flips, rail advances, auto-navigate to matrix. Reject: dialog requires a note, returns to TRIAGED.
- Loading: skeleton rows on muted surfaces, no content spinners. Error: inline danger card with retry, never a blank screen. Empty: start-run card. FAILED: full-width danger banner with last transition and actor.
- Keyboard: Esc closes panel/dialog, arrows move matrix row selection, Enter opens drilldown. Focus rings per design system (`0 0 0 3px rgba(67,56,202,.08)` + indigo border).
- Accessibility: chips carry text labels (never color-only), aria-live on the run state chip, focus trap in panel and dialogs, AA contrast in both themes.

## 6. Frontend architecture

Stack additions (mirrors project-seo):

- Tailwind CSS v4 (`@tailwindcss/vite`), single `@theme` block for all tokens, `.dark` custom variant.
- shadcn/ui primitives, restyled with the tokens: button, badge, card, dialog, input, table, skeleton, tooltip. No second component library.
- `@pierre/diffs` (^1.2) for diff rendering.
- `@fontsource-variable/geist`, `@fontsource-variable/geist-mono`.
- No router, no state library. One React context.

File map (kebab-case per `frontend/AGENTS.md`; existing PascalCase files are renamed as part of this work):

```
frontend/src/
├── styles/theme.css              # @theme tokens, light + dark
├── api/client.ts                 # extended: patches list, approve, reject, rerun; USE_API flag kept
├── state/run-context.tsx         # run polling, view selection, selected failure, mock state driver
├── app.tsx                       # shell: title bar, rail, stage view, drilldown panel host
├── components/
│   ├── ui/                       # shadcn primitives
│   ├── pipeline-rail.tsx         # includes pinned model-actions card
│   ├── model-actions-panel.tsx
│   ├── status-chip.tsx           # frozen enum -> style map (exhaustive switch, no default invented states)
│   ├── stat-tiles.tsx
│   ├── failure-card.tsx
│   ├── diff-viewer.tsx           # @pierre/diffs wrapper + FAIL line annotations + focus filter
│   └── record-drilldown-panel.tsx
└── screens/
    ├── run-start.tsx
    ├── run-progress.tsx
    ├── traceability-matrix.tsx
    ├── approval-gate.tsx
    └── run-comparison.tsx
```

Data flow:

- `api/client.ts` remains the only data source. `USE_API=false` serves mocks; `true` hits `/api`. The swap stays a data-source change.
- Mock state driver (fixture runs only): the backend fixture API is frozen at RUN-001 = PATCH_PENDING, so `run-context` simulates the frozen state machine client-side to demo the full loop: approve moves PATCH_PENDING to PATCH_APPROVED to RERUNNING (rows flip) to EVIDENCE_READY. The driver activates whenever the run's `mode` is `fixture`, regardless of whether data comes from mocks or the fixture API; runs with `mode: live` use real polling of `GET /api/runs/{id}` instead. Transitions honor the frozen enum exactly; the driver is unit-tested against it. The FIXTURE badge is always visible while the driver is active (integrity rule).
- Fix-location chips (Seen/Fix) derive from parsing the patch diff hunks client-side (file + first changed line per failure mapping). When the mapping is ambiguous the chip degrades to file-only.

Testing:

- `bun lint` (Biome + tsc + knip) stays the single check command; `bun test` for units.
- Unit tests: status-chip mapping is exhaustive over the frozen enums; mock state driver only produces legal transitions; diff hunk parser handles multi-file diffs.
- Mocks stay contract-valid (backend CI already validates `frontend/src/mocks/` against `contracts/`); frontend tests import the same fixtures rather than inventing shapes.

## 7. Out of scope / cut order

Out of scope: backend changes, contracts, fixtures content, evidence HTML styling, multi-run history, responsive mobile layout (desktop-first for demo; content min-width ~1100px).

If time runs short, cut in this order (never cut the matrix, the approval gate diff, or mode labeling):

1. Keyboard navigation on the matrix
2. Click-to-focus diff filtering (keep hover cross-highlight)
3. Dark theme toggle (light stays complete)
4. Run comparison animations (static before/after is fine)

## 8. References

- `ARCHITECTURE.md` v2.2 (frozen), sections 4, 5, 6, 11
- `design-system.md` (repo root)
- project-seo tokens: `~/workspace/pivanov/cloudstrap/project-seo/packages/web/src/index.css`
- Approved mockups (local only, gitignored): `.superpowers/brainstorm/*/content/design-system-v4.html` (light), `design-system-v4-dark.html` (dark), `option-b-v3.html` (cross-linking interaction)
