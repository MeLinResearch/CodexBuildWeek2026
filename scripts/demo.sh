#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pytest backend/tests >/dev/null
echo "Fixture demo ready"
