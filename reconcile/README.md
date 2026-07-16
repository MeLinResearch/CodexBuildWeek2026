# Reconcile

Purpose: Vendored deterministic record-reconciliation engine for future use by Release Assurance.

Status: The vendored deterministic engine remains isolated and tested. `reconcile/migration.py` is separate new Build Week code: a deliberately flawed migration target for the live Codex repair demonstration. It is not wired into the backend API, Store, fixture pipeline, frontend, or normal demo runtime.

Owner: Melinda Emerson / MeLinResearch.

## Provenance

- Pre-existing code created before OpenAI Build Week.
- Original repository: https://github.com/MeLinResearch/Reconcile
- Imported commit SHA: b280ed49388791f3cae7fa2fc88144c2c706bd9d
- Original license: MIT. The original license is retained in `reconcile/LICENSE`.

## Build Week changes

- Moved the engine into the hackathon repository's `reconcile` Python package.
- Preserved deterministic transformation, coercion, validation, retry feedback, and escalation behavior.
- Removed the upstream Anthropic client and all environment-key switching.
- Kept the mapping proposer injectable so a future validated backend LLM edge can supply mapping proposals.
- Retained only the deterministic heuristic proposer for offline use.
- Added deterministic source-field and synonym ordering for stable tie-breaking.
- Moved the original example data into `reconcile/fixtures/`.
- Adapted the upstream tests to run inside the hackathon repository's existing backend test suite.
- `migration.py` was added as deliberately flawed deterministic Build Week code for the live Codex repair demonstration and was not part of the imported upstream Reconcile repository.

## Integration boundary

`reconcile/` must not import from `backend/`.

The planted migration target must remain isolated until the approval-gated live workflow is implemented.

A future live mapping proposal must be created and schema-validated outside this package before being injected into `reconcile()`.

This vendoring task does not change API behavior, pipeline behavior, Store persistence, contracts, frontend behavior, `make demo`, or `make demo-live`.
