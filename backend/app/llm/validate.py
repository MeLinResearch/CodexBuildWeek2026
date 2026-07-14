from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver

from app.config import REPO_ROOT
from app.llm.client import JsonObject

CONTRACTS_DIR = REPO_ROOT / "contracts"
CONTROL_MANIFEST_SCHEMA = "control_manifest.schema.json"


def _load_json(path: Path) -> JsonObject:
    with path.open(encoding="utf-8") as handle:
        data: Any = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _contract_store() -> dict[str, JsonObject]:
    return {path.name: _load_json(path) for path in CONTRACTS_DIR.glob("*.schema.json")}


def validate_against_contract(payload: JsonObject, schema_name: str) -> JsonObject:
    """Validate a model-shaped JSON object against a frozen contract schema."""
    schema_path = CONTRACTS_DIR / schema_name
    schema = _load_json(schema_path)
    store = _contract_store()
    resolver = RefResolver(base_uri=schema_path.as_uri(), referrer=schema, store=store)
    Draft202012Validator(schema, resolver=resolver).validate(payload)
    return payload


def validate_control_manifest(payload: JsonObject) -> JsonObject:
    """Validate a requirements control manifest model output."""
    return validate_against_contract(payload, CONTROL_MANIFEST_SCHEMA)
