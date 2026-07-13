#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make setup
make test
make demo
