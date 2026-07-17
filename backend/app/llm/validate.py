from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver, ValidationError

from app.config import REPO_ROOT
from app.llm.client import JsonObject

CONTRACTS_DIR = REPO_ROOT / "contracts"
CONTROL_MANIFEST_SCHEMA = "control_manifest.schema.json"


@FormatChecker.cls_checks("date-time")
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


def bundle_schema_for_model(schema_name: str) -> JsonObject:
    """Return a detached schema with local contract references bundled in $defs."""
    root = deepcopy(load_schema(schema_name))
    definitions: JsonObject = deepcopy(root.get("$defs", {}))
    loaded: dict[str, str] = {}

    def bundle(value: Any) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.endswith(".schema.json") and "/" not in reference:
                definition_name = loaded.get(reference)
                if definition_name is None:
                    definition_name = reference.removesuffix(".schema.json")
                    loaded[reference] = definition_name
                    referenced = deepcopy(load_schema(reference))
                    referenced.pop("$schema", None)
                    referenced.pop("$id", None)
                    bundle(referenced)
                    definitions[definition_name] = referenced
                value["$ref"] = f"#/$defs/{definition_name}"
            for child in list(value.values()):
                bundle(child)
        elif isinstance(value, list):
            for child in value:
                bundle(child)

    root.pop("$schema", None)
    root.pop("$id", None)
    bundle(root)
    if definitions:
        root["$defs"] = definitions
    _make_strict(root)
    return root


def _make_strict(value: Any) -> None:
    """Adapt the detached model schema to the strict Structured Outputs subset."""
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            required = set(value.get("required", []))
            for name, child in properties.items():
                if name not in required and isinstance(child, dict):
                    child_type = child.get("type")
                    if isinstance(child_type, str):
                        child["type"] = [child_type, "null"]
                    elif isinstance(child_type, list) and "null" not in child_type:
                        child["type"] = [*child_type, "null"]
            value["required"] = list(properties)
        for child in value.values():
            _make_strict(child)
    elif isinstance(value, list):
        for child in value:
            _make_strict(child)


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
        validator = Draft202012Validator(
            schema,
            resolver=resolver,
            format_checker=FormatChecker(),
        )
        validator.validate(payload)
    except ValidationError as error:
        raise LLMValidationError(schema_name, error.message, tuple(error.path)) from error
    return payload


def validate_against_contract(payload: JsonObject, schema_name: str) -> JsonObject:
    return validate_output(schema_name, payload)


def validate_control_manifest(payload: JsonObject) -> JsonObject:
    return validate_output(CONTROL_MANIFEST_SCHEMA, payload)
