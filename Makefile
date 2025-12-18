.PHONY: help install venv run docker-build docker-up docker-down docker-run docker-logs load-db reload test lint format clean tree

# Image tag (override with: make docker-build TAG=myorg/myapp:dev)
TAG ?= kg-wiki-api:latest

help:
	@echo "Commands:"
	@echo "  make venv          Create local virtualenv (.venv)"
	@echo "  make install       Install requirements into .venv"
	@echo "  make run           Run FastAPI (uvicorn) on :8000"
	@echo "  make docker-build  Build Docker image (TAG=$(TAG))"
	@echo "  make docker-up     Start all services (Neo4j + API + Nginx)"
	@echo "  make docker-down   Stop all services"
	@echo "  make docker-run    Run full stack with Docker Compose"
	@echo "  make docker-logs   Show logs from all containers"
	@echo "  make load-db       Load database from Cypher script"
	@echo "  make reload        Restart and reload database"
	@echo "  make test          Run pytest with coverage"
	@echo "  make lint          Run pylint (if configured)"
	@echo "  make format        Run black code formatter"
	@echo "  make clean         Remove caches and temp files"
	@echo "  make tree          Show project tree (depth 3)"

venv:
	@if [ ! -d ".venv" ]; then \
		python3 -m venv .venv; \
		. .venv/bin/activate && pip install --upgrade pip; \
		echo "Created .venv"; \
	else echo ".venv already exists"; fi
	@echo "To activate: source .venv/bin/activate"

install: venv
	@. .venv/bin/activate && pip install -r requirements.txt
	@echo "Dependencies installed successfully!"

run:
	@. .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	@echo "Building Docker image..."
	docker build -t $(TAG) .
	@echo "Image built: $(TAG)"

docker-up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services started. API available at http://localhost:80"
	@echo "Neo4j browser available at http://localhost:7474"

docker-down:
	@echo "Stopping all services..."
	docker-compose down

docker-run: docker-build docker-up
	@echo "Full stack is running!"
	@echo "Access the API at: http://localhost:80"
	@echo "Access Neo4j browser at: http://localhost:7474"
	@echo "View logs with: make docker-logs"

docker-logs:
	docker-compose logs -f

load-db:
	@echo "Loading database..."
	@./load_database.sh
	@echo "Database loaded successfully!"

reload: docker-down docker-up load-db
	@echo "Database reloaded successfully!"

test:
	@echo "Running tests with coverage..."
	@if [ -d ".venv" ]; then \
		. .venv/bin/activate && pytest; \
	else \
		pytest; \
	fi

lint:
	@echo "Running pylint..."
	@if command -v pylint >/dev/null 2>&1; then \
		pylint app || true; \
	else echo "pylint not installed (add to requirements.txt)"; fi

format:
	@echo "Formatting code with black..."
	@if command -v black >/dev/null 2>&1; then \
		black app tests -l 120; \
	else echo "black not installed (add to requirements.txt)"; fi

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -prune -exec rm -rf {} \; 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage 2>/dev/null || true
	@echo "Cleanup complete!"

tree:
	@if command -v tree >/dev/null 2>&1; then \
		tree -L 3 -I "node_modules|dist|.git|.venv|__pycache__|htmlcov|.pytest_cache|neo4j_data|neo4j_logs"; \
	else \
		find . -maxdepth 3 -type d -not -path '*/\.*' | sort; \
	fi
