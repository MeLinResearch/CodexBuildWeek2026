from html import escape

from fastapi import APIRouter, Response

from app.config import PATCH_ID_FIXTURE
from app.routers.runs import require_run
from app.store.db import Store

router = APIRouter(prefix="/api")


@router.get("/runs/{run_id}/evidence", response_class=Response)
def evidence(run_id: str):
    run = require_run(run_id)
    store = Store()
    requirements = store.list_requirements(run_id)
    failures = store.list_failures(run_id)
    patch = store.get_patch(PATCH_ID_FIXTURE)

    requirement_items = "".join(f"<li>{escape(requirement.text)}</li>" for requirement in requirements)
    failure_items = "".join(f"<li>{escape(failure.failure_id)}</li>" for failure in failures)
    patch_html = f"<p>{escape(PATCH_ID_FIXTURE)}</p>" if patch is not None else ""
    html = (
        "<!doctype html><html><head><title>Release Assurance Evidence Pack</title></head>"
        "<body><h1>Release Assurance Evidence Pack</h1>"
        f"<p>run_id {escape(run.run_id)}</p>"
        f"<p>mode {escape(run.mode)}</p>"
        f"<ul>{requirement_items}</ul>"
        f"<ul>{failure_items}</ul>"
        f"{patch_html}"
        "<p>Fixture evidence, no live model calls</p>"
        "</body></html>"
    )
    return Response(content=html, media_type="text/html")
