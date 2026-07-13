import json
from pathlib import Path
from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"
SCHEMAS = {p.name: json.loads(p.read_text()) for p in CONTRACTS.glob("*.schema.json")}

def load(path):
    return json.loads(path.read_text())

def validate(name, data):
    schema = SCHEMAS[name]
    resolver = RefResolver(base_uri=schema["$id"].rsplit("/", 1)[0] + "/", referrer=schema, store={s["$id"]: s for s in SCHEMAS.values()})
    Draft202012Validator(schema, resolver=resolver).validate(data)

def test_all_json_valid():
    for base in [ROOT / "fixtures", ROOT / "frontend/src/mocks"]:
        for path in sorted(base.rglob("*.json")):
            load(path)

def test_fixture_contracts():
    validate("run_status.schema.json", load(ROOT / "fixtures/api/run_status.fixture.json"))
    for row in load(ROOT / "fixtures/api/traceability_matrix.fixture.json"):
        validate("traceability_row.schema.json", row)
    for fid in ["FAIL-001", "FAIL-002", "FAIL-003"]:
        validate("failed_record.schema.json", load(ROOT / f"fixtures/api/failed_record_{fid}.fixture.json"))
    validate("patch_proposal.schema.json", load(ROOT / "fixtures/api/patch_PATCH-001.fixture.json"))
    validate("summary_stats.schema.json", load(ROOT / "fixtures/api/summary_stats.fixture.json"))
    validate("control_manifest.schema.json", load(ROOT / "fixtures/model_outputs/control_manifest.fixture.json"))

def test_frontend_mocks_match_backend_fixtures():
    pairs = ["run_status.fixture.json", "traceability_matrix.fixture.json", "patch_PATCH-001.fixture.json", "summary_stats.fixture.json", "failed_record_FAIL-001.fixture.json"]
    for name in pairs:
        assert load(ROOT / "frontend/src/mocks" / name) == load(ROOT / "fixtures/api" / name)
