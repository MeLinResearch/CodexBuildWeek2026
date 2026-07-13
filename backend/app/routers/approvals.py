from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import PATCH_ID_FIXTURE
from app.store.db import Store

router = APIRouter(prefix="/api")


class ApprovalRequest(BaseModel):
    actor: str
    note: str | None = None


def _require_patch(patch_id: str):
    if patch_id != PATCH_ID_FIXTURE:
        raise HTTPException(status_code=404, detail="patch not found")
    store = Store()
    store.init_schema()
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


@router.get("/patches/{patch_id}")
def get_patch(patch_id: str):
    return _patch_payload(_require_patch(patch_id))


@router.post("/patches/{patch_id}/approve")
def approve_patch(patch_id: str, request: ApprovalRequest):
    _require_patch(patch_id)
    return {"patch_id": patch_id, "status": "approved", "actor": request.actor, "note": request.note}


@router.post("/patches/{patch_id}/reject")
def reject_patch(patch_id: str, request: ApprovalRequest):
    _require_patch(patch_id)
    return {"patch_id": patch_id, "status": "rejected", "actor": request.actor, "note": request.note}
