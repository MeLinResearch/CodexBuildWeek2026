from app.main import app
from app import config
from app.routers.runs import _fallback_provenance
from app.store.db import Store
from app.store.models import ArtifactRow


def test_api_has_general_release_assurance_title():
    assert app.title == "Release Assurance API"


def test_failed_live_run_fallback_uses_live_identity(tmp_path):
    store = Store(tmp_path / "store.db", clock=lambda: "2026-07-17T00:00:00Z")
    store.init_schema()
    run = store.create_run("live", config.SCHEMA_VERSION, state="FAILED", run_id="RUN-002")
    store.insert_artifact(ArtifactRow("ART-010", run.run_id, "input", "fixtures/input.md", "sha256",
                                      "deterministic", "live", "none", "not_required", run.created_at))

    provenance = _fallback_provenance(run, store)

    assert provenance["run_id"] == "RUN-002"
    assert provenance["mode"] == "live"
    assert provenance["client"] == "LiveLLMClient"
    assert provenance["source_artifact_ids"] == ["ART-010"]
    assert provenance["validation_status"] == "rejected"
