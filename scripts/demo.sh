#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=backend python -m pytest backend/tests/test_contracts.py backend/tests/test_fixtures.py backend/tests/test_api_fixture_mode.py >/dev/null
echo "Fixture demo ready"
