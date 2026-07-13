from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app import fixture_loader
from app.config import PATCH_ID_FIXTURE

router = APIRouter(prefix="/api")

class ApprovalRequest(BaseModel):
    actor: str
    note: str | None = None

def require_patch(patch_id: str):
    if patch_id != PATCH_ID_FIXTURE:
        raise HTTPException(status_code=404, detail="patch not found")

@router.get("/patches/{patch_id}")
def get_patch(patch_id: str):
    require_patch(patch_id)
    return fixture_loader.patch(patch_id)

@router.post("/patches/{patch_id}/approve")
def approve_patch(patch_id: str, request: ApprovalRequest):
    require_patch(patch_id)
    return {"patch_id": patch_id, "status": "approved", "actor": request.actor, "note": request.note}

@router.post("/patches/{patch_id}/reject")
def reject_patch(patch_id: str, request: ApprovalRequest):
    require_patch(patch_id)
    return {"patch_id": patch_id, "status": "rejected", "actor": request.actor, "note": request.note}
