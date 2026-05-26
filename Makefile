setup:
	powershell -NoProfile -Command "if (!(Test-Path .env)) { Copy-Item .env.example .env }"
	docker compose pull

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

generate-data:
	python src/generators/generate_all.py

run-quality-gate:
	python src/validation/quality_gate.py

run-bronze:
	python src/transformations/bronze_ingest.py

run-silver:
	python src/transformations/silver_clean.py

run-gold:
	python src/transformations/gold_star_schema.py

load-gold-postgres:
	python src/sql/load_gold_to_postgres.py

load-gold-iceberg:
	docker exec keuangan-spark-master /opt/spark/bin/spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1,org.apache.iceberg:iceberg-aws-bundle:1.10.1,org.postgresql:postgresql:42.7.3 /opt/lakehouse/src/transformations/load_gold_iceberg.py

run-metrics:
	python src/metrics/reconcile_control_total.py
	python src/metrics/pipeline_latency.py
	python src/metrics/data_freshness.py
	python src/metrics/dropout_rate.py
	python src/metrics/data_quality_score.py
	python src/metrics/generate_uat.py

setup-superset:
	python src/sql/setup_superset_assets.py
	python src/sql/setup_superset_dashboard.py

check-ports:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_ports.ps1

test:
	python -m pytest tests/ -v

full-run: generate-data run-quality-gate run-bronze run-silver run-gold run-metrics load-gold-postgres load-gold-iceberg setup-superset test
