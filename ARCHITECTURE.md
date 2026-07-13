ARCHITECTURE.md — v2.2 FROZEN FINAL (2026-07-12)

Project title:
Release Assurance: Codex-Gated Migration Testing for Banks

One-liner:
It turns a bank conversion spec into executable migration tests, maps every failure back to a requirement, lets Codex propose fixes, and produces an audit-ready evidence pack after approval.

Governing principle:
Deterministic core, LLMs at the edges. Every model output validates against a JSON Schema in contracts/ before entering the pipeline. No raw model text ever touches financial records. The repo structure itself demonstrates this thesis.

This document is the source of truth for all Codex tasks. Codex must read it and contracts/ before any edit, and must never invent field names, state names, API routes, or schema properties.

This scaffold was created from the frozen architecture source block supplied in the task prompt.
