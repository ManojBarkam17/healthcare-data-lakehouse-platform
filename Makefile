.PHONY: help install lint test demo-full demo-light generate-data \
       bronze silver gold dbt-run dbt-test dbt-docs streamlit clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Setup ────────────────────────────────────────────────────────────────────

install: ## Install Python dependencies
	pip install -r requirements-dev.txt

install-dev: ## Install dev + test dependencies
	pip install -r requirements-dev.txt
	pip install ruff mypy pytest pytest-cov

# ─── Code Quality ─────────────────────────────────────────────────────────────

lint: ## Run linter (ruff)
	ruff check src/ tests/ dags/
	ruff format --check src/ tests/ dags/

format: ## Auto-format code
	ruff format src/ tests/ dags/
	ruff check --fix src/ tests/ dags/

test: ## Run unit tests
	pytest tests/unit -v --tb=short

test-cov: ## Run tests with coverage
	pytest tests/unit -v --cov=src --cov-report=html --cov-report=term

# ─── Data Generation ──────────────────────────────────────────────────────────

generate-data: ## Generate synthetic healthcare data
	python -m src.ingestion.generate_data

# ─── Pipeline Stages ──────────────────────────────────────────────────────────

bronze: ## Run Bronze ingestion (raw -> Delta)
	python -m src.transformations.bronze.ingest

silver: ## Run Silver transformations (cleanse + validate)
	python -m src.transformations.silver.transform

gold: ## Run Gold dimensional model build
	python -m src.transformations.gold.build_dimensions

pipeline: generate-data bronze silver gold ## Run full pipeline end-to-end

# ─── dbt ──────────────────────────────────────────────────────────────────────

dbt-run: ## Run dbt models
	cd dbt_project && dbt run

dbt-test: ## Run dbt tests
	cd dbt_project && dbt test

dbt-docs: ## Generate and serve dbt docs
	cd dbt_project && dbt docs generate && dbt docs serve --port 8081

# ─── Data Quality ─────────────────────────────────────────────────────────────

validate: ## Run Great Expectations validation
	python -m src.quality.validate

# ─── Dashboard ────────────────────────────────────────────────────────────────

streamlit: ## Launch Streamlit dashboard
	streamlit run streamlit_app/app.py --server.port 8501

# ─── Demo Modes ───────────────────────────────────────────────────────────────

demo-full: ## Full Docker Compose stack (16GB RAM required)
	docker compose -f infrastructure/docker/docker-compose-airflow.yml up --build

demo-light: ## Lightweight local demo (8GB RAM, no Docker)
	@echo "=== Healthcare Data Lakehouse - Light Demo ==="
	@echo "Generating synthetic data..."
	python -m src.ingestion.generate_data --scale small
	@echo "Running Bronze ingestion..."
	python -m src.transformations.bronze.ingest
	@echo "Running Silver transformations..."
	python -m src.transformations.silver.transform
	@echo "Building Gold dimensions..."
	python -m src.transformations.gold.build_dimensions
	@echo "Running dbt models..."
	cd dbt_project && dbt run && dbt test
	@echo "Launching dashboard..."
	streamlit run streamlit_app/app.py --server.port 8501

# ─── Docker ───────────────────────────────────────────────────────────────────

docker-up: ## Start Docker services
	docker compose -f infrastructure/docker/docker-compose-airflow.yml up -d

docker-down: ## Stop Docker services
	docker compose -f infrastructure/docker/docker-compose-airflow.yml down -v

# ─── Cleanup ──────────────────────────────────────────────────────────────────

clean: ## Remove generated data and build artifacts
	rm -rf data/raw/*.csv data/raw/*.json
	rm -rf data/bronze/ data/silver/ data/gold/
	rm -rf dbt_project/target/ dbt_project/dbt_packages/ dbt_project/logs/
	rm -rf spark-warehouse/ metastore_db/ derby.log
	rm -rf .pytest_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
