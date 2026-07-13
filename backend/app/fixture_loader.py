import json
from pathlib import Path
from .config import API_FIXTURES_DIR, PATCH_ID_FIXTURE

def load_json(path: Path):
    return json.loads(path.read_text())

def api_fixture(name: str):
    return load_json(API_FIXTURES_DIR / name)

def run_status():
    return api_fixture("run_status.fixture.json")

def matrix():
    return api_fixture("traceability_matrix.fixture.json")

def failure(failure_id: str):
    return api_fixture(f"failed_record_{failure_id}.fixture.json")

def patch(patch_id: str):
    if patch_id != PATCH_ID_FIXTURE:
        raise FileNotFoundError(patch_id)
    return api_fixture("patch_PATCH-001.fixture.json")
