from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import RUN_ID_FIXTURE
from app import fixture_loader

router = APIRouter(prefix="/api")

class RunRequest(BaseModel):
    mode: str
    fixture_set: str | None = None
    implementation_doc_path: str | None = None
    source_data_path: str | None = None
    target_schema_path: str | None = None

def require_run(run_id: str):
    if run_id != RUN_ID_FIXTURE:
        raise HTTPException(status_code=404, detail="run not found")

@router.post("/runs")
def create_run(request: RunRequest):
    if request.mode != "fixture":
        raise HTTPException(status_code=400, detail="live mode is not implemented in scaffold")
    return {"run_id": RUN_ID_FIXTURE}

@router.get("/runs/{run_id}")
def get_run(run_id: str):
    require_run(run_id)
    return fixture_loader.run_status()

@router.get("/runs/{run_id}/matrix")
def get_matrix(run_id: str):
    require_run(run_id)
    return fixture_loader.matrix()

@router.get("/runs/{run_id}/failures/{failure_id}")
def get_failure(run_id: str, failure_id: str):
    require_run(run_id)
    try:
        return fixture_loader.failure(failure_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="failure not found") from None

@router.get("/runs/{run_id}/patches")
def get_patches(run_id: str):
    require_run(run_id)
    return [fixture_loader.patch("PATCH-001")]

@router.post("/runs/{run_id}/rerun")
def rerun(run_id: str):
    require_run(run_id)
    return {"run_id": run_id, "status": "rerun accepted", "mode": "fixture"}
