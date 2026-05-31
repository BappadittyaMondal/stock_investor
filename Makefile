# HFOS v5.0 Platform Automation Makefile
# Simplifying deployment, execution, testing, and operations

.PHONY: setup init-db test run build docker-up docker-down clean lint

PYTHON = python
PIP = pip
STREAMLIT = streamlit

setup:
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt

init-db:
	@echo "Initializing SQLite production schema..."
	$(PYTHON) -c "from database.db_manager import initialize_schema; initialize_schema()"

test:
	@echo "Executing Pytest suite (Unit & Integration)..."
	$(PYTHON) -m pytest -v tests/

run:
	@echo "Launching Streamlit application portal..."
	$(STREAMLIT) run main.py

build:
	@echo "Building production Docker image..."
	docker build -t hfos-platform:latest .

docker-up:
	@echo "Orchestrating container deployment in background..."
	docker-compose -f deployment/docker-compose.yml up -d

docker-down:
	@echo "Terminating orchestrated container service..."
	docker-compose -f deployment/docker-compose.yml down

clean:
	@echo "Cleaning compiled pyc files and caches..."
	rm -rf __pycache__ */__pycache__ */*/__pycache__ .pytest_cache
	@echo "To completely reset database cache, manually delete e:\stock_invest\database\hfos_production.db"

lint:
	@echo "Checking codebase compliance..."
	black --check . || echo "Install 'black' for standard formatting check"
