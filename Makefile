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
	spark-submit src/transformations/bronze_ingest.py

run-silver:
	spark-submit src/transformations/silver_clean.py

run-gold:
	spark-submit src/transformations/gold_star_schema.py

run-metrics:
	python src/metrics/reconcile_control_total.py
	python src/metrics/pipeline_latency.py
	python src/metrics/data_freshness.py
	python src/metrics/dropout_rate.py
	python src/metrics/data_quality_score.py

test:
	pytest tests/ -v

full-run: generate-data run-quality-gate run-bronze run-silver run-gold run-metrics test

