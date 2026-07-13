from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures"
API_FIXTURES_DIR = FIXTURES_DIR / "api"
GPT_MODEL_NAME = "gpt-5.6"
CODEX_TASK_ID_FIXTURE = "fixture"
RUN_ID_FIXTURE = "RUN-001"
PATCH_ID_FIXTURE = "PATCH-001"
