PYTHON ?= python
BUN ?= bun

.PHONY: setup test demo demo-live dev smoke runtime-smoke

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e "backend[dev]"
	cd frontend && $(BUN) install --frozen-lockfile

test:
	$(PYTHON) -m pytest backend/tests
	cd frontend && $(BUN) lint
	cd frontend && $(BUN) test
	cd frontend && $(BUN) run build

demo:
	$(PYTHON) scripts/runtime_smoke.py

demo-live:
	$(BUN) run scripts/demo-live.ts

dev:
	cd frontend && $(BUN) run dev

runtime-smoke:
	$(PYTHON) scripts/runtime_smoke.py

smoke:
	$(MAKE) setup
	$(MAKE) test
	$(MAKE) demo
