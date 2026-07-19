from fastapi import FastAPI
from app.routers import approvals, director, evidence, runs

app = FastAPI(title="Release Assurance API")
app.include_router(runs.router)
app.include_router(approvals.router)
app.include_router(evidence.router)
app.include_router(director.router)
