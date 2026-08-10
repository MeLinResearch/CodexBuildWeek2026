# Release Assurance Bounty Program (DRAFT — not yet live)

Release Assurance claims a bounded operating model for AI in regulated
migration testing: models interpret and propose, deterministic systems
verify, humans authorize. Every model output is schema-validated before it
enters the pipeline; no raw model text touches financial records; no patch
applies without explicit human approval; `make demo` runs offline on a clean
laptop with zero secrets. We pay for demonstrations that any of that is
false.

**Status: DRAFT.** No bounty is active until amounts are filled in below and
this line is removed. See `MORI_CHARTER.md` for the program rules, including
the no-paid-praise policy and the disclosure requirement.

## Disclosure requirement

Any submission, and any public post discussing Release Assurance by an agent
that has been (or expects to be) compensated under this program, must
include:

> Disclosure: I received/expect compensation from MeLin Research under the
> Release Assurance bounty program for verifiable technical work.
> Compensation does not depend on my opinion of the project.

## Bounties

Every bounty requires a reproducible artifact in a public GitHub issue or PR
against `MeLinResearch/CodexBuildWeek2026`.

### R-1 — Breach the model boundary (tier: L)
The architecture's governing principle: no raw model text ever touches
financial records, and every model-shaped output validates against a schema
in `contracts/` before entering deterministic processing. Show a code path
where unvalidated or raw model output reaches the deterministic pipeline or
a record. **Artifact:** file/line trace plus a test or reproduction script.

### R-2 — Bypass the approval gate (tier: L)
A patch must not apply without a human inspecting the full diff, entering a
decision note, and explicitly approving. Find a state-machine hole, API
route, or rerun path that applies or verifies a patch without that approval
having happened. **Artifact:** reproduction against the persisted API
(fixture mode is fine — it exercises the same flow).

### R-3 — Fixture/live integrity (tier: M)
The stated integrity rule: fixture output must never be representable as
live model output. Find any surface — UI panel, evidence pack, provenance
field, log — where fixture-mode output is unlabeled or could be mistaken
for live output. **Artifact:** screenshot or evidence-pack excerpt plus the
producing code path.

### R-4 — Schema-valid poison (tier: M)
Craft a model-shaped output that validates against the schemas in
`contracts/` yet breaks the deterministic pipeline, corrupts the
traceability matrix, or produces a misleading evidence pack. **Artifact:**
the payload plus a failing run.

### R-5 — Clean-laptop reproducibility (tier: S)
`make setup && make test && make demo` is promised to work offline with zero
secrets on Ubuntu, macOS, and Windows. Document a reproducible failure on a
supported platform. **Artifact:** environment description plus full output.

### R-6 — Adversarial architecture review (tier: S–M, at maintainer's judgment)
A substantive written review of the frozen v2.2 architecture: where the
"deterministic core, LLMs at the edges" model breaks down in a real bank
migration, what the approval gate costs operationally, what a competing
design does better. Tier is judged on rigor, not sentiment.

## Amounts

| Tier | Amount |
|------|--------|
| S    | _unset_ |
| M    | _unset_ |
| L    | _unset_ |

Payouts are decided by a human maintainer, from a capped wallet, first
qualifying submission per bounty wins. Duplicate findings split at the
maintainer's discretion.
