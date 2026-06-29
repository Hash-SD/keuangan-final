from __future__ import annotations

import os
from pathlib import Path

from pyspark.sql import SparkSession


ROOT = Path("/opt/lakehouse")
GOLD_DIR = ROOT / "data" / "generated" / "gold"


def main() -> None:
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY") or os.getenv("MINIO_ROOT_USER") or os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_ROOT_PASSWORD") or os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
    minio_bucket = os.getenv("MINIO_BUCKET", "lakehouse")
    iceberg_warehouse = os.getenv("ICEBERG_WAREHOUSE", f"s3://{minio_bucket}/warehouse")
    spark = (
        SparkSession.builder.appName("load-gold-iceberg")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.iceberg.type", "jdbc")
        .config("spark.sql.catalog.iceberg.jdbc.catalog-name", "lakehouse")
        .config("spark.sql.catalog.iceberg.uri", "jdbc:postgresql://postgres-metastore:5432/metastore")
        .config("spark.sql.catalog.iceberg.jdbc.user", "lakehouse")
        .config("spark.sql.catalog.iceberg.jdbc.password", "lakehouse")
        .config("spark.sql.catalog.iceberg.warehouse", iceberg_warehouse)
        .config("spark.sql.catalog.iceberg.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.iceberg.s3.endpoint", minio_endpoint)
        .config("spark.sql.catalog.iceberg.s3.access-key-id", minio_access_key)
        .config("spark.sql.catalog.iceberg.s3.secret-access-key", minio_secret_key)
        .config("spark.sql.catalog.iceberg.s3.path-style-access", "true")
        .config("spark.sql.catalog.iceberg.client.region", "us-east-1")
        .config("spark.sql.defaultCatalog", "iceberg")
        .getOrCreate()
    )
    spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.gold")

    table_names = [
        "dim_organisasi",
        "dim_mahasiswa",
        "dim_kualitas_piutang",
        "dim_waktu_tunggakan",
        "fact_piutang_ukt_prodi",
        "vw_dashboard_piutang_ukt",
        "fact_anggaran",
        "vw_dashboard_iku_anggaran",
        "vw_dashboard_mapping_quality",
        "vw_dashboard_reconciliation",
        "vw_dashboard_detail_item",
    ]
    for table_name in table_names:
        path = GOLD_DIR / f"{table_name}.csv"
        if not path.exists():
            print(f"skip iceberg.gold.{table_name}: {path} not found")
            continue
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(str(path))
        df.writeTo(f"iceberg.gold.{table_name}").using("iceberg").createOrReplace()
        print(f"wrote iceberg.gold.{table_name}: {df.count()} rows")

    spark.stop()


if __name__ == "__main__":
    main()
