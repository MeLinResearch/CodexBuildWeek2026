#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

cmp -s "Frozen Architecture v2.2/ARCHITECTURE.md" ARCHITECTURE.md

test ! -e backend/fastapi
test ! -e backend/jsonschema.py
test ! -e backend/pydantic.py
test ! -e backend/pytest.py
test ! -e backend/httpx.py

if git ls-files | grep -E '(__pycache__/|\.pyc$|\.pyo$)'; then
  echo "Tracked Python cache artifacts found"
  exit 1
fi

test -s frontend/package-lock.json

node -e "const fs=require('fs'); const lock=JSON.parse(fs.readFileSync('frontend/package-lock.json','utf8')); if (!lock.packages || Object.keys(lock.packages).length < 10) { throw new Error('package-lock.json appears fake or incomplete'); }"

if grep -R '"/api/runs/RUN-001/summary"\|/api/runs/RUN-001/summary' frontend/src backend/app; then
  echo "Invented summary API route found"
  exit 1
fi

if grep -R '"latest"' frontend/package.json; then
  echo "latest dependency found"
  exit 1
fi

echo "handoff check ready"
