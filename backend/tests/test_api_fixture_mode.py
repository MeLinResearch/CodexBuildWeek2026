from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_fixture_endpoints_without_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert client.post("/api/runs", json={"mode": "fixture", "fixture_set": "bank_migration_demo_v1"}).json() == {"run_id": "RUN-001"}
    assert client.get("/api/runs/RUN-001").status_code == 200
    assert client.get("/api/runs/RUN-001/matrix").status_code == 200
    assert client.get("/api/runs/RUN-001/failures/FAIL-001").status_code == 200
    assert client.get("/api/runs/RUN-001/patches").status_code == 200
    assert client.get("/api/patches/PATCH-001").status_code == 200
    assert client.post("/api/patches/PATCH-001/approve", json={"actor": "demo_user", "note": "optional"}).json()["status"] == "approved"
    assert client.post("/api/patches/PATCH-001/reject", json={"actor": "demo_user", "note": "optional"}).json()["status"] == "rejected"
    assert client.post("/api/runs/RUN-001/rerun").status_code == 200
    evidence = client.get("/api/runs/RUN-001/evidence")
    assert evidence.status_code == 200
    assert "Fixture evidence, no live model calls" in evidence.text

def test_unknown_ids_404():
    assert client.get("/api/runs/RUN-999").status_code == 404
    assert client.get("/api/patches/PATCH-999").status_code == 404
    assert client.get("/api/runs/RUN-001/failures/FAIL-999").status_code == 404
