from fastapi import APIRouter, HTTPException, Response

from app.evidence import render_evidence_html
from app.routers.runs import build_matrix, require_run
from app.store.db import Store

router = APIRouter(prefix="/api")


@router.get("/runs/{run_id}/evidence", response_class=Response)
def evidence(run_id: str):
    run = require_run(run_id)
    store = Store()
    store.init_schema()
    requirements = store.list_requirements(run_id)
    if not requirements:
        raise HTTPException(status_code=404, detail="requirements not found")
    tests = store.list_tests(run_id)
    failures = store.list_failures(run_id)
    patches = store.list_patches(run_id)
    if len(patches) != 1:
        raise HTTPException(status_code=404, detail="patch not found")
    patch = patches[0]
    transitions = store.list_state_transitions(run_id)
    matrix = build_matrix(store, run_id)
    html = render_evidence_html(
        run=run,
        requirements=requirements,
        tests=tests,
        failures=failures,
        patch=patch,
        matrix=matrix,
        transitions=transitions,
    )
    return Response(content=html, media_type="text/html")
