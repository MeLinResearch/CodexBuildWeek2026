from __future__ import annotations

import hashlib
import json
from app import fixture_loader
from app.config import FIXTURES_DIR, REPO_ROOT
from app.store.db import Store
from app.store.models import ArtifactRow, FailureRow, PatchRow, RequirementRow, RunRow, TestRow
from app.store.state_machine import transition_run


def _sha256_fixture(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest() -> dict:
    return json.loads((FIXTURES_DIR / "model_outputs" / "control_manifest.fixture.json").read_text())


def run_fixture_pipeline(
    store: Store,
    *,
    run_id: str = "RUN-001",
    actor: str = "mock_pipeline",
) -> RunRow:
    store.init_schema()

    existing = store.get_run(run_id)
    if existing is not None:
        return existing

    run_status = fixture_loader.run_status()
    matrix = fixture_loader.matrix()
    patch = fixture_loader.patch("PATCH-001")
    manifest = _load_manifest()
    failures = [fixture_loader.failure(failure_id) for failure_id in ["FAIL-001", "FAIL-002", "FAIL-003"]]

    store.create_run("fixture", run_status["schema_version"], state="CREATED", run_id=run_id)

    created_at = run_status["created_at"]
    for artifact_id, kind, path, producer, client, validation_status in [
        (
            "ART-001",
            "input",
            "fixtures/implementation_doc.md",
            "deterministic",
            "none",
            "not_required",
        ),
        (
            "ART-002",
            "validated_model_output",
            "fixtures/model_outputs/control_manifest.fixture.json",
            "fixture",
            "FixtureLLMClient",
            "validated",
        ),
        (
            "ART-006",
            "test_output",
            "fixtures/api/failed_record_FAIL-001.fixture.json",
            "fixture",
            "FixtureLLMClient",
            "validated",
        ),
        (
            "ART-007",
            "test_output",
            "fixtures/api/failed_record_FAIL-002.fixture.json",
            "fixture",
            "FixtureLLMClient",
            "validated",
        ),
        (
            "ART-008",
            "test_output",
            "fixtures/api/failed_record_FAIL-003.fixture.json",
            "fixture",
            "FixtureLLMClient",
            "validated",
        ),
        (
            "ART-009",
            "patch_diff",
            "fixtures/api/patch_PATCH-001.fixture.json",
            "fixture",
            "FixtureCodexClient",
            "validated",
        ),
    ]:
        store.insert_artifact(
            ArtifactRow(
                artifact_id=artifact_id,
                run_id=run_id,
                kind=kind,
                path=path,
                sha256=_sha256_fixture(path),
                producer=producer,
                mode="fixture",
                client=client,
                validation_status=validation_status,
                created_at=created_at,
            )
        )

    transition_run(store, run_id, "INGESTED", actor)

    requirement_text_by_id: dict[str, str] = {}
    for requirement in manifest["requirements"]:
        requirement_text_by_id[requirement["requirement_id"]] = requirement["text"]
        store.insert_requirement(
            RequirementRow(
                requirement_id=requirement["requirement_id"],
                run_id=run_id,
                text=requirement["text"],
                rule_type=requirement["rule_type"],
                tolerance=requirement.get("tolerance"),
                provenance=requirement["provenance"],
            )
        )

    transition_run(store, run_id, "MANIFEST_READY", actor)

    test_id_by_failure_id: dict[str, str] = {}
    for row in matrix:
        for failure_id in row["failure_ids"]:
            test_id_by_failure_id[failure_id] = row["test_id"]
        store.insert_test(
            TestRow(
                test_id=row["test_id"],
                run_id=run_id,
                requirement_id=row["requirement_id"],
                name=requirement_text_by_id[row["requirement_id"]],
                status="failed",
                output_ref=row["evidence_refs"][0],
                provenance=row["provenance"],
            )
        )

    transition_run(store, run_id, "TESTS_GENERATED", actor)

    for failure in failures:
        store.insert_failure(
            FailureRow(
                failure_id=failure["failure_id"],
                run_id=run_id,
                requirement_id=failure["requirement_id"],
                test_id=test_id_by_failure_id[failure["failure_id"]],
                record_id=failure["record_id"],
                field=failure["field"],
                expected=failure["expected"],
                actual=failure["actual"],
                severity=failure["severity"],
                record_hash=failure["record_hash"],
                provenance=failure["provenance"],
            )
        )

    transition_run(store, run_id, "EXECUTED", actor)
    transition_run(store, run_id, "TRIAGED", actor)

    store.insert_patch(
        PatchRow(
            patch_id="PATCH-001",
            run_id=run_id,
            failure_ids=["FAIL-001", "FAIL-002", "FAIL-003"],
            diff=patch["diff"],
            status="pending",
            approved_by=None,
            approved_at=None,
            applied_at=None,
            provenance=patch["provenance"],
        )
    )

    transition_run(store, run_id, "PATCH_PENDING", actor)

    final_run = store.get_run(run_id)
    assert final_run is not None
    return final_run
