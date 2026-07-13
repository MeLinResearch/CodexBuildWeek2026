from fastapi import FastAPI
from app.routers import approvals, runs

app = FastAPI(title="Release Assurance Fixture API")
app.include_router(runs.router)
app.include_router(approvals.router)
