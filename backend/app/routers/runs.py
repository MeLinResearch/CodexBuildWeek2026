from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import config
from app.config import PATCH_ID_FIXTURE, RUN_ID_FIXTURE
from app.pipeline.mock_pipeline import run_fixture_pipeline
from app.store.db import Store
from app.store.state_machine import InvalidTransitionError, RunNotFoundError, transition_run

router = APIRouter(prefix="/api")

RUN_PROVENANCE_FALLBACK = {
    "client": "FixtureLLMClient",
    "created_at": config.FIXTURE_CLOCK_AT,
    "mode": "fixture",
    "producer": "fixture",
    "run_id": "RUN-001",
    "schema_version": "2026-07-12.1",
    "source_artifact_ids": ["ART-001"],
    "validation_status": "validated",
}


class RunRequest(BaseModel):
    mode: str
    fixture_set: str | None = None
    implementation_doc_path: str | None = None
    source_data_path: str | None = None
    target_schema_path: str | None = None


def _store() -> Store:
    return Store(clock=config.fixture_clock)


def _require_fixture_run_id(run_id: str) -> None:
    if run_id != RUN_ID_FIXTURE:
        raise HTTPException(status_code=404, detail="run not found")


def require_run(run_id: str):
    _require_fixture_run_id(run_id)
    store = _store()
    store.init_schema()
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


def _matrix_row_status(patch_status: str) -> str:
    status_by_patch_status = {
        "pending": "patch_pending",
        "approved": "patch_approved",
        "rejected": "failed",
        "applied": "rerun_passed",
        "apply_failed": "failed",
    }
    return status_by_patch_status.get(patch_status, "failed")


def build_matrix(store: Store, run_id: str) -> list[dict]:
    tests = store.list_tests(run_id)
    failures = store.list_failures(run_id)
    patch = store.get_patch(PATCH_ID_FIXTURE)
    if patch is None:
        raise HTTPException(status_code=404, detail="patch not found")

    rows = []
    for test in tests:
        failure_ids = sorted(
            failure.failure_id for failure in failures if failure.test_id == test.test_id
        )
        if not any(failure_id in patch.failure_ids for failure_id in failure_ids):
            raise HTTPException(status_code=404, detail="patch not found")
        rows.append(
            {
                "requirement_id": test.requirement_id,
                "test_id": test.test_id,
                "failure_ids": failure_ids,
                "patch_id": PATCH_ID_FIXTURE,
                "row_status": _matrix_row_status(patch.status),
                "evidence_refs": [test.output_ref] if test.output_ref is not None else [],
                "provenance": test.provenance,
            }
        )
    return rows


def _patch_payload(patch):
    return {
        "patch_id": patch.patch_id,
        "run_id": patch.run_id,
        "failure_ids": patch.failure_ids,
        "diff": patch.diff,
        "status": patch.status,
        "provenance": patch.provenance,
    }


@router.post("/runs")
def create_run(request: RunRequest):
    if request.mode != "fixture":
        raise HTTPException(status_code=400, detail="live mode is not implemented in scaffold")
    store = _store()
    store.init_schema()
    store.delete_run(RUN_ID_FIXTURE)
    run_fixture_pipeline(store, run_id=RUN_ID_FIXTURE, actor="api")
    return {"run_id": RUN_ID_FIXTURE}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    run = require_run(run_id)
    requirements = _store().list_requirements(run_id)
    provenance = requirements[0].provenance if requirements else RUN_PROVENANCE_FALLBACK
    return {
        "run_id": run.run_id,
        "state": run.state,
        "mode": run.mode,
        "schema_version": run.schema_version,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "provenance": provenance,
    }


@router.get("/runs/{run_id}/matrix")
def get_matrix(run_id: str):
    require_run(run_id)
    store = _store()
    return build_matrix(store, run_id)


@router.get("/runs/{run_id}/failures/{failure_id}")
def get_failure(run_id: str, failure_id: str):
    require_run(run_id)
    failure = _store().get_failure(failure_id)
    if failure is None or failure.run_id != run_id:
        raise HTTPException(status_code=404, detail="failure not found")
    return {
        "failure_id": failure.failure_id,
        "record_id": failure.record_id,
        "requirement_id": failure.requirement_id,
        "field": failure.field,
        "expected": failure.expected,
        "actual": failure.actual,
        "severity": failure.severity,
        "record_hash": failure.record_hash,
        "provenance": failure.provenance,
    }


@router.get("/runs/{run_id}/patches")
def get_patches(run_id: str):
    require_run(run_id)
    return [_patch_payload(patch) for patch in _store().list_patches(run_id)]


@router.post("/runs/{run_id}/rerun")
def rerun(run_id: str):
    run = require_run(run_id)
    if run.state != "PATCH_APPROVED":
        raise HTTPException(status_code=409, detail="run is not approved for rerun")
    store = _store()
    try:
        transition_run(store, run_id, "RERUNNING", actor="api")
        store.mark_patch_applied(PATCH_ID_FIXTURE)
        transition_run(store, run_id, "EVIDENCE_READY", actor="api")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RunNotFoundError, LookupError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "run_id": run_id,
        "status": "rerun complete",
        "state": "EVIDENCE_READY",
        "mode": "fixture",
    }
