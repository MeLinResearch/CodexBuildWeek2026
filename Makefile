PYTHON ?= python3

.PHONY: setup test demo dev smoke

setup:
	cd frontend && npm install

test:
	cd backend && PYTHONPATH=. pytest
	cd frontend && npm run build

demo:
	./scripts/demo.sh

dev:
	@echo "Backend: http://127.0.0.1:8000"
	@echo "Frontend: http://127.0.0.1:5173"
	(cd backend && PYTHONPATH=. python -m app.main) & cd frontend && npm run dev

smoke:
	$(MAKE) setup
	$(MAKE) test
	$(MAKE) demo
