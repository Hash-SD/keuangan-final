setup:
	powershell -NoProfile -Command "if (!(Test-Path .env)) { Copy-Item .env.example .env }"
	docker compose pull

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

run-pipeline:
	python src/transformations/excel_lakehouse_pipeline.py

validate-counts:
	python src/validation/excel_count_validation.py

storage-manifest:
	python src/storage/excel_storage_manifest.py

load-gold-postgres:
	python src/sql/load_gold_to_postgres.py

setup-superset:
	python src/sql/setup_superset_excel_assets.py

truth-status:
	python src/status/system_truth_status.py

run-metrics:
	python src/metrics/pipeline_latency.py
	python src/metrics/data_freshness.py
	python src/metrics/generate_uat.py

check-ports:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_ports.ps1

test:
	python -m pytest tests/ -v

full-run: run-pipeline validate-counts storage-manifest load-gold-postgres setup-superset truth-status test
