from __future__ import annotations

from datetime import datetime
import re
from typing import Any

_NUMERIC_CLEANUP_RE = re.compile(r"[,$_\s]")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TRUE_VALUES = {"true", "yes", "y", "1", "t", "active"}
_FALSE_VALUES = {"false", "no", "n", "0", "f", "inactive"}
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%b %d, %Y",
    "%B %d, %Y",
    "%b %d %Y",
    "%B %d %Y",
)


def coerce_value(raw: Any, target_type: str) -> Any:
    if raw is None:
        return None

    if target_type == "string":
        value = str(raw).strip()
        return value or None

    if target_type == "integer":
        value = _NUMERIC_CLEANUP_RE.sub("", str(raw))
        if value == "":
            return None
        try:
            parsed = float(value)
        except ValueError:
            return None
        if not parsed.is_integer():
            return None
        return int(parsed)

    if target_type == "number":
        value = _NUMERIC_CLEANUP_RE.sub("", str(raw))
        if value == "":
            return None
        try:
            return float(value)
        except ValueError:
            return None

    if target_type == "boolean":
        value = str(raw).strip().lower()
        if value in _TRUE_VALUES:
            return True
        if value in _FALSE_VALUES:
            return False
        return None

    if target_type == "date":
        value = str(raw).strip()
        if value == "":
            return None
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
        return None

    if target_type == "email":
        value = str(raw).strip().lower()
        if value == "":
            return None
        return value if _EMAIL_RE.match(value) else None

    value = str(raw).strip()
    return value or None


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected in ("date", "email"):
        return isinstance(value, str) and value != ""
    return True


def validate_record(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for name, spec in schema.get("fields", {}).items():
        value = record.get(name)
        required = spec.get("required", False)
        expected = spec.get("type", "string")

        if required and (value is None or value == ""):
            errors.append(f"missing required field '{name}'")
            continue

        if value is None or value == "":
            continue

        if not _type_ok(value, expected):
            errors.append(f"field '{name}' failed type '{expected}' (got {value!r})")
            continue

        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"field '{name}' value {value!r} not in allowed set {spec['enum']}")

    return errors
