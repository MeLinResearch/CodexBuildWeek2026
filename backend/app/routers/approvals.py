from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import config
from app.store.db import Store
from app.store.state_machine import InvalidTransitionError, RunNotFoundError, transition_run

router = APIRouter(prefix="/api")


class ApprovalRequest(BaseModel):
    actor: str
    note: str | None = None


def _store(clock=config.default_clock) -> Store:
    store = Store(clock=clock)
    store.init_schema()
    return store


def _require_patch(store: Store, patch_id: str):
    patch = store.get_patch(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="patch not found")
    return patch


def _patch_payload(patch):
    return {
        "patch_id": patch.patch_id,
        "run_id": patch.run_id,
        "failure_ids": patch.failure_ids,
        "diff": patch.diff,
        "status": patch.status,
        "provenance": patch.provenance,
    }


def _decide_patch(patch_id: str, request: ApprovalRequest, status: str, to_state: str):
    store = _store()
    patch = _require_patch(store, patch_id)
    run = store.get_run(patch.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.mode == "fixture":
        store = _store(config.fixture_clock); patch = _require_patch(store, patch_id); run = store.get_run(patch.run_id)
    if run.state != "PATCH_PENDING":
        raise HTTPException(status_code=409, detail="run is not awaiting patch decision")
    if patch.status != "pending":
        raise HTTPException(status_code=409, detail="patch decision already recorded")
    try:
        transition_run(store, patch.run_id, to_state, actor=request.actor)
        store.set_patch_decision(patch_id, status, request.actor)
    except (InvalidTransitionError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RunNotFoundError, LookupError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"patch_id": patch_id, "status": status, "actor": request.actor, "note": request.note}


@router.get("/patches/{patch_id}")
def get_patch(patch_id: str):
    store = _store()
    return _patch_payload(_require_patch(store, patch_id))


@router.post("/patches/{patch_id}/approve")
def approve_patch(patch_id: str, request: ApprovalRequest):
    return _decide_patch(patch_id, request, "approved", "PATCH_APPROVED")


@router.post("/patches/{patch_id}/reject")
def reject_patch(patch_id: str, request: ApprovalRequest):
    return _decide_patch(patch_id, request, "rejected", "PATCH_REJECTED")
