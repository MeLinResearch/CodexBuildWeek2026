PYTHON ?= python3

.PHONY: setup test demo dev smoke

setup:
	python -m pip install --upgrade pip
	python -m pip install -e "backend[dev]"
	cd frontend && npm ci

test:
	scripts/handoff_check.sh
	python -m pytest backend/tests
	cd frontend && npm run build

demo:
	./scripts/demo.sh

dev:
	@echo "Backend: http://127.0.0.1:8000"
	@echo "Frontend: http://127.0.0.1:5173"
	(uvicorn app.main:app --app-dir backend --reload) & cd frontend && npm run dev

smoke:
	$(MAKE) setup
	$(MAKE) test
	$(MAKE) demo
