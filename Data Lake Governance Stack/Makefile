.PHONY: init ingest transform validate serve test docs all clean rebuild help

# Permite sobreescribir el interprete: make all PYTHON=python3
PYTHON ?= python

# Default target
all: init ingest transform validate serve

# Initialize environment
init:
	docker compose up -d
	$(PYTHON) -m pip install -r requirements.txt
	@if [ ! -f great_expectations/great_expectations.yml ]; then \
		echo "Initializing Great Expectations..."; \
		gx init --config-dir great_expectations; \
	else \
		echo "GX already initialized"; \
	fi

# Download and convert Olist data to partitioned Parquet
ingest:
	$(PYTHON) scripts/ingest.py

# Transform raw to curated
transform:
	$(PYTHON) scripts/transform.py

# Validate Great Expectations config (structural check of suites + checkpoints)
validate:
	$(PYTHON) scripts/gx_run_checkpoint.py

# Build serving layer and configure Superset
serve:
	$(PYTHON) scripts/build_serving.py
	$(PYTHON) scripts/superset_init.py

# Run tests
test:
	$(PYTHON) -m pytest tests/ -v --cov=scripts --cov-report=term-missing

# Show generated documentation locations
docs:
	@echo "Data Docs available at: great_expectations/uncommitted/data_docs/local_site/index.html"
	@echo "Superset available at: http://localhost:8088 (admin/admin)"

# Clean generated data (preserves structure)
clean:
	rm -rf data_lake/00_landing data_lake/01_raw data_lake/02_curated data_lake/03_serving
	mkdir -p data_lake/00_landing data_lake/01_raw data_lake/02_curated data_lake/03_serving
	@echo "Data directories cleaned and recreated"

# Full rebuild from scratch
rebuild: clean all

# Help
help:
	@echo "Available targets:"
	@echo "  init      - Start Docker services and install dependencies"
	@echo "  ingest    - Download Olist data and convert to partitioned Parquet"
	@echo "  transform - Clean and enrich raw data to curated layer"
	@echo "  validate  - Validate Great Expectations config (suites + checkpoints)"
	@echo "  serve     - Build serving layer and configure Superset"
	@echo "  test      - Run pytest suite"
	@echo "  docs      - Show documentation URLs"
	@echo "  all       - Run full pipeline (default)"
	@echo "  clean     - Remove all generated data"
	@echo "  rebuild   - Clean and rebuild everything"
