from __future__ import annotations

from datetime import datetime
import re
from typing import Any

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
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
_TRUE_VALUES = {"true", "yes", "y", "1", "t", "active"}
_FALSE_VALUES = {"false", "no", "n", "0", "f", "inactive"}


def _clean_numeric(raw: Any) -> str:
    return "".join(str(raw).replace(",", "").replace("$", "").replace("_", "").split())


def coerce_value(raw: Any, target_type: str) -> Any:
    if raw is None:
        return None

    target_type = (target_type or "string").lower()

    if target_type == "string":
        value = str(raw).strip()
        return value if value else None

    if target_type == "integer":
        value = _clean_numeric(raw)
        if not value:
            return None
        try:
            parsed = float(value)
        except ValueError:
            return None
        if not parsed.is_integer():
            return None
        return int(parsed)

    if target_type == "number":
        value = _clean_numeric(raw)
        if not value:
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
        if not value:
            return None
        for date_format in _DATE_FORMATS:
            try:
                return datetime.strptime(value, date_format).date().isoformat()
            except ValueError:
                pass
        return None

    if target_type == "email":
        value = str(raw).strip().lower()
        if not value:
            return None
        return value if _EMAIL_RE.match(value) else None

    value = str(raw).strip()
    return value if value else None


def validate_record(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fields = schema.get("fields", {})

    for field, definition in fields.items():
        value = record.get(field)
        target_type = definition.get("type", "string")
        required = definition.get("required", False)

        if required and (value is None or value == ""):
            errors.append(f"missing required field '{field}'")
            continue

        if value is None or value == "":
            continue

        if target_type == "string" and not isinstance(value, str):
            errors.append(f"field '{field}' expected string")
        elif target_type == "integer" and not isinstance(value, int):
            errors.append(f"field '{field}' expected integer")
        elif target_type == "number" and not isinstance(value, (int, float)):
            errors.append(f"field '{field}' expected number")
        elif target_type == "boolean" and not isinstance(value, bool):
            errors.append(f"field '{field}' expected boolean")
        elif target_type == "date" and not isinstance(value, str):
            errors.append(f"field '{field}' expected date")
        elif target_type == "email" and not (isinstance(value, str) and _EMAIL_RE.match(value)):
            errors.append(f"field '{field}' expected email")

        if "enum" in definition and value not in definition["enum"]:
            errors.append(f"field '{field}' must be one of {definition['enum']}")

    return errors
