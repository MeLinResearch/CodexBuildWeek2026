from pathlib import Path

import fastapi
import jsonschema
import pydantic
import pytest


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_LOCAL_STUBS = [
    ROOT / "backend" / "jsonschema.py",
    ROOT / "backend" / "pydantic.py",
    ROOT / "backend" / "fastapi",
    ROOT / "backend" / "pytest.py",
    ROOT / "backend" / "httpx.py",
]


def test_forbidden_local_dependency_stubs_do_not_exist():
    for path in FORBIDDEN_LOCAL_STUBS:
        assert not path.exists(), f"Local dependency stub must not exist: {path}"


def test_dependency_imports_resolve_outside_repository():
    for module in [fastapi, pydantic, jsonschema, pytest]:
        module_path = Path(module.__file__).resolve()
        assert not module_path.is_relative_to(ROOT), (
            f"{module.__name__} resolved to repo-local path {module_path}; "
            "install the real package instead of shadowing it"
        )
