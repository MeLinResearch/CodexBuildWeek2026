from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:9011"
FIXTURE_REQUEST = {"mode": "fixture", "fixture_set": "core-banking"}


def request(method: str, path: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=5) as response:
        body = response.read()
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return json.loads(body.decode("utf-8"))
        return body.decode("utf-8")


def wait_for_server() -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            request("GET", "/api/runs/RUN-001")
        except urllib.error.HTTPError:
            return
        except Exception:
            time.sleep(0.25)
        else:
            return
    raise RuntimeError("Uvicorn did not respond within 15 seconds")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["RELEASE_ASSURANCE_DB_PATH"] = str(Path(tmp) / "runtime.sqlite")
        env["FIXED_CLOCK"] = "2026-07-12T00:00:00Z"
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "9011"],
            env=env,
        )
        try:
            wait_for_server()
            assert request("POST", "/api/runs", FIXTURE_REQUEST) == {"run_id": "RUN-001"}
            assert request("GET", "/api/runs/RUN-001")["state"] == "PATCH_PENDING"
            approved = request("POST", "/api/patches/PATCH-001/approve", {"actor": "melinda.emerson", "note": "Runtime smoke approval"})
            assert approved["status"] == "approved"
            rerun = request("POST", "/api/runs/RUN-001/rerun")
            assert rerun["status"] == "rerun complete"
            assert rerun["state"] == "EVIDENCE_READY"
            assert rerun["mode"] == "fixture"
            assert request("GET", "/api/runs/RUN-001")["state"] == "EVIDENCE_READY"
            matrix = request("GET", "/api/runs/RUN-001/matrix")
            assert all(row["row_status"] == "rerun_passed" for row in matrix)
            rerun_artifact_ids = {row["evidence_refs"][0] for row in matrix}
            assert len(rerun_artifact_ids) == 1
            assert rerun_artifact_ids.isdisjoint({"ART-006", "ART-007", "ART-008"})
            report_path = Path(__file__).resolve().parents[1] / ".release_assurance/runs/RUN-001/rerun_result.json"
            report = json.loads(report_path.read_text())
            assert report["artifact_id"] in rerun_artifact_ids
            assert set(report["checks"].values()) == {"passed"}
            html = request("GET", "/api/runs/RUN-001/evidence")
            for expected in [
                "Release Assurance Evidence Pack",
                "Run provenance",
                "Traceability matrix",
                "Failure evidence",
                "Proposed patch",
                "Decision record",
                "State transition audit trail",
                "RUN-001",
                "PATCH-001",
                "FAIL-001",
                "melinda.emerson",
                "Fixture evidence, no live model calls",
            ]:
                assert expected in html
            assert request("POST", "/api/runs", FIXTURE_REQUEST) == {"run_id": "RUN-001"}
            assert request("GET", "/api/runs/RUN-001")["state"] == "PATCH_PENDING"
            assert request("GET", "/api/patches/PATCH-001")["status"] == "pending"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    print("FastAPI fixture runtime smoke ready")


if __name__ == "__main__":
    main()
