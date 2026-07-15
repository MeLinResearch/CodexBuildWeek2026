PYTHON ?= python3
BUN ?= bun

.PHONY: setup test demo dev smoke

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
	./scripts/demo.sh

dev:
	@echo "Mock API: http://127.0.0.1:9001"
	@echo "Frontend: http://127.0.0.1:9000"
	cd frontend && $(BUN) run dev

smoke:
	$(MAKE) setup
	$(MAKE) test
	$(MAKE) demo
