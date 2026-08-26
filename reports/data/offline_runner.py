"""Deterministic offline extractor stub.

Wired in via the repo's own RUNNER_IMPORT_PATH knob (api_v1/runner_loader.py)
so the legal-ingest route can be exercised with no OPENAI_API_KEY and no
network. Emits zero candidates, which is a valid ExtractorOutput.
"""
from __future__ import annotations
from typing import Any


def extract_instances_runner(text: str, user_id=None, now_iso=None, request_id=None) -> dict[str, Any]:
    return {
        "candidates": [],
        "version_meta": {"ruleset_version": "v1", "prompt_version": "offline-stub-v1"},
        "extraction_source": "offline_stub",
    }
