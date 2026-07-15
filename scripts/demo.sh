#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/runtime_smoke.py
echo "Fixture demo ready"
