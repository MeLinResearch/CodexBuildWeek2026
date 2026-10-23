PYTHON ?= python
BUN ?= bun

.PHONY: setup test demo demo-live dev smoke runtime-smoke

setup:
	$(PYTHON) -m pip install --no-cache-dir "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
	$(PYTHON) -m pip install --upgrade "certifi>=2026.10.19"
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
