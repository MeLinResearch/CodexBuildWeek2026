from fastapi import APIRouter, Response

from app.routers.runs import require_run

router = APIRouter(prefix="/api")


@router.get("/runs/{run_id}/evidence", response_class=Response)
def evidence(run_id: str):
    require_run(run_id)
    html = """<!doctype html><html><head><title>Release Assurance Evidence Pack</title></head><body><h1>Release Assurance Evidence Pack</h1><p>run_id RUN-001</p><p>mode fixture</p><ul><li>preserve account identifiers verbatim</li><li>debits equal credits by branch</li><li>no silent value substitution</li></ul><ul><li>FAIL-001</li><li>FAIL-002</li><li>FAIL-003</li></ul><p>PATCH-001</p><p>Fixture evidence, no live model calls</p></body></html>"""
    return Response(content=html, media_type="text/html")
