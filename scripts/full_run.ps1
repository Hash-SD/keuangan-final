$ErrorActionPreference = "Stop"

python src/generators/generate_all.py
python src/validation/quality_gate.py
python src/transformations/bronze_ingest.py
python src/transformations/silver_clean.py
python src/transformations/gold_star_schema.py
python src/metrics/reconcile_control_total.py
python src/metrics/pipeline_latency.py
python src/metrics/data_freshness.py
python src/metrics/dropout_rate.py
python src/metrics/data_quality_score.py
python src/metrics/generate_uat.py
python src/sql/load_gold_to_postgres.py
docker exec keuangan-spark-master /opt/spark/bin/spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1,org.apache.iceberg:iceberg-aws-bundle:1.10.1,org.postgresql:postgresql:42.7.3 /opt/lakehouse/src/transformations/load_gold_iceberg.py
python src/sql/setup_superset_assets.py
python src/sql/setup_superset_dashboard.py
python -m pytest tests -v
