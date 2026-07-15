from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver, ValidationError

from app.config import REPO_ROOT
from app.llm.client import JsonObject

CONTRACTS_DIR = REPO_ROOT / "contracts"
CONTROL_MANIFEST_SCHEMA = "control_manifest.schema.json"
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time")
def _is_date_time(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    try:
        datetime.fromisoformat(instance.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


class LLMValidationError(ValueError):
    def __init__(self, schema_name: str, message: str, path: tuple[str | int, ...]) -> None:
        super().__init__(f"{schema_name}: {message}")
        self.schema_name = schema_name
        self.message = message
        self.path = path


def _load_json_object(path: Path) -> JsonObject:
    with path.open(encoding="utf-8") as handle:
        data: Any = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def load_schema(schema_name: str) -> JsonObject:
    """Load a frozen JSON Schema contract by filename."""
    schema_path = CONTRACTS_DIR / schema_name
    if not schema_path.is_file():
        raise FileNotFoundError(schema_path)
    return _load_json_object(schema_path)


def _contract_store() -> dict[str, JsonObject]:
    store: dict[str, JsonObject] = {}
    for path in CONTRACTS_DIR.glob("*.schema.json"):
        schema = _load_json_object(path)
        store[path.name] = schema
        store[path.as_uri()] = schema
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            store[schema_id] = schema
    return store


def validate_output(schema_name: str, payload: JsonObject) -> JsonObject:
    """Validate a model-shaped JSON object against a frozen contract schema."""
    schema_path = CONTRACTS_DIR / schema_name
    schema = load_schema(schema_name)
    store = _contract_store()
    resolver = RefResolver(base_uri=schema_path.as_uri(), referrer=schema, store=store)
    try:
        Draft202012Validator(schema, resolver=resolver, format_checker=FORMAT_CHECKER).validate(payload)
    except ValidationError as error:
        raise LLMValidationError(schema_name, error.message, tuple(error.path)) from error
    return payload


def validate_against_contract(payload: JsonObject, schema_name: str) -> JsonObject:
    return validate_output(schema_name, payload)


def validate_control_manifest(payload: JsonObject) -> JsonObject:
    return validate_output(CONTROL_MANIFEST_SCHEMA, payload)
