from __future__ import annotations

import re
from typing import Any

_SYNONYMS = {
    "email": {"emailaddress", "mail", "contactemail", "e"},
    "fullname": {"name", "customername", "client", "fullname"},
    "amount": {"total", "price", "cost", "value", "amt"},
    "signupdate": {"created", "createdat", "joined", "date", "registered"},
    "active": {"isactive", "status", "enabled"},
}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _source_fields(sample: list[dict[str, Any]]) -> list[str]:
    fields: set[str] = set()
    for record in sample:
        for key in record:
            if key is not None:
                fields.add(key)
    return sorted(fields)


def _pick_source(target_field: str, sources: list[str], normalized_sources: dict[str, list[str]]) -> str | None:
    normalized_target = _normalize(target_field)

    exact = normalized_sources.get(normalized_target)
    if exact:
        return sorted(exact)[0]

    if len(normalized_target) >= 3:
        for source in sorted(sources):
            normalized_source = _normalize(source)
            if len(normalized_source) >= 3 and (
                normalized_target in normalized_source or normalized_source in normalized_target
            ):
                return source

    for synonym in sorted(_SYNONYMS.get(normalized_target, set())):
        if len(synonym) < 3:
            continue
        for source in sorted(sources):
            normalized_source = _normalize(source)
            if len(normalized_source) >= 3 and normalized_source == synonym:
                return source

    return None


def propose_mapping(
    *,
    sample: list[dict[str, Any]],
    target_schema: dict[str, Any],
    previous_mapping: dict[str, Any] | None = None,
    failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    del previous_mapping, failures
    sources = _source_fields(sample)
    normalized_sources: dict[str, list[str]] = {}
    for source in sources:
        normalized_sources.setdefault(_normalize(source), []).append(source)

    mapping: dict[str, Any] = {}
    for target_field, definition in target_schema.get("fields", {}).items():
        mapping[target_field] = {
            "source": _pick_source(target_field, sources, normalized_sources),
            "type": definition.get("type", "string"),
        }
    return mapping
