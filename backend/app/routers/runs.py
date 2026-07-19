import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import config
from app.config import RUN_ID_FIXTURE
from app.codex.live_client import LiveCodexClient
from app.llm.live_client import LiveLLMClient, LiveLLMConfigurationError
from app.pipeline.live_pipeline import LiveInputError, LivePipelineError, LiveRunInputs, run_live_pipeline
from app.pipeline.live_rerun import LiveRerunError, apply_and_verify_patch
from pathlib import Path
from app.pipeline.mock_pipeline import run_fixture_pipeline
from app.store.db import Store
from app.store.state_machine import InvalidTransitionError, RunNotFoundError, transition_run

router = APIRouter(prefix="/api")

logger = logging.getLogger("release_assurance.runs")

FIXTURE_PROVENANCE_FALLBACK = {
    "client": "FixtureLLMClient",
    "created_at": config.FIXTURE_CLOCK_AT,
    "mode": "fixture",
    "producer": "fixture",
    "run_id": "RUN-001",
    "schema_version": "2026-07-12.1",
    "source_artifact_ids": ["ART-001"],
    "validation_status": "validated",
}


def _fallback_provenance(run, store: Store) -> dict:
    if run.mode == "fixture":
        return {**FIXTURE_PROVENANCE_FALLBACK, "run_id": run.run_id,
                "schema_version": run.schema_version, "created_at": run.created_at}
    return {
        "client": "LiveLLMClient",
        "created_at": run.created_at,
        "mode": "live",
        "producer": "gpt-5.6",
        "run_id": run.run_id,
        "schema_version": run.schema_version,
        "source_artifact_ids": [artifact.artifact_id for artifact in store.list_artifacts(run.run_id)
                                if artifact.kind == "input"],
        "validation_status": "rejected" if run.state == "FAILED" else "quarantined",
    }


class RunRequest(BaseModel):
    mode: str
    fixture_set: str | None = None
    implementation_doc_path: str | None = None
    source_data_path: str | None = None
    target_schema_path: str | None = None


def _store() -> Store:
    return Store()

def _make_live_llm_client(): return LiveLLMClient()
def _make_live_codex_client(): return LiveCodexClient()


def require_run(run_id: str):
    store = _store()
    store.init_schema()
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


def _matrix_row_status(patch_status: str, test_status: str) -> str:
    if patch_status == "applied":
        return "rerun_passed" if test_status == "passed" else "failed"
    status_by_patch_status = {
        "pending": "patch_pending",
        "approved": "patch_approved",
        "rejected": "failed",
        "apply_failed": "failed",
    }
    return status_by_patch_status.get(patch_status, "failed")


def build_matrix(store: Store, run_id: str) -> list[dict]:
    tests = store.list_tests(run_id)
    failures = store.list_failures(run_id)
    patches = store.list_patches(run_id)
    if len(patches) != 1:
        raise HTTPException(status_code=404, detail="patch not found")
    patch = patches[0]

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
                "patch_id": patch.patch_id,
                "row_status": _matrix_row_status(patch.status, test.status),
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
    if request.mode == "fixture":
        store = Store(clock=config.fixture_clock); store.init_schema(); store.delete_run(RUN_ID_FIXTURE)
        run_fixture_pipeline(store, run_id=RUN_ID_FIXTURE, actor="api"); return {"run_id": RUN_ID_FIXTURE}
    if request.mode != "live" or request.fixture_set is not None or not all((request.implementation_doc_path, request.source_data_path, request.target_schema_path)):
        raise HTTPException(status_code=400, detail="live mode requires three input paths and no fixture_set")
    inputs = LiveRunInputs(Path(request.implementation_doc_path), Path(request.source_data_path), Path(request.target_schema_path))
    try: run = run_live_pipeline(_store(), inputs, _make_live_llm_client(), _make_live_codex_client())
    except LiveInputError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LiveLLMConfigurationError as exc: raise HTTPException(status_code=503, detail="live LLM is not configured") from exc
    except LivePipelineError as exc:
        logger.exception("live pipeline failed at stage %s (run %s)", exc.stage, exc.run_id)
        raise HTTPException(status_code=502, detail={"run_id": exc.run_id, "stage": exc.stage}) from exc
    except Exception as exc:
        logger.exception("live run failed before reaching the pipeline")
        raise HTTPException(status_code=500, detail="live pipeline failed") from exc
    return {"run_id": run.run_id}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    run = require_run(run_id)
    store = _store()
    requirements = store.list_requirements(run_id)
    provenance = requirements[0].provenance if requirements else _fallback_provenance(run, store)
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
    store = Store(clock=config.fixture_clock if run.mode == "fixture" else config.default_clock)
    store.init_schema()
    patches = store.list_patches(run_id)
    if len(patches) != 1: raise HTTPException(status_code=404, detail="patch not found")
    patch = patches[0]
    try:
        apply_and_verify_patch(store, patch)
        transition_run(store, run_id, "RERUNNING", actor="api")
        transition_run(store, run_id, "EVIDENCE_READY", actor="api")
    except LiveRerunError as exc:
        logger.exception("disposable rerun failed for %s (%s)", run_id, patch.patch_id)
        store.set_patch_application(patch.patch_id, "apply_failed", patch.provenance)
        transition_run(store, run_id, "FAILED", actor="api")
        raise HTTPException(status_code=422, detail="approved patch failed disposable verification") from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RunNotFoundError, LookupError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "run_id": run_id,
        "status": "rerun complete",
        "state": "EVIDENCE_READY",
        "mode": run.mode,
    }
