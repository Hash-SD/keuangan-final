from __future__ import annotations

from pathlib import Path

from pyspark.sql import SparkSession


ROOT = Path("/opt/lakehouse")
GOLD_DIR = ROOT / "data" / "generated" / "gold"


def main() -> None:
    spark = (
        SparkSession.builder.appName("load-gold-iceberg")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.iceberg.type", "jdbc")
        .config("spark.sql.catalog.iceberg.jdbc.catalog-name", "lakehouse")
        .config("spark.sql.catalog.iceberg.uri", "jdbc:postgresql://postgres-metastore:5432/metastore")
        .config("spark.sql.catalog.iceberg.jdbc.user", "lakehouse")
        .config("spark.sql.catalog.iceberg.jdbc.password", "lakehouse")
        .config("spark.sql.catalog.iceberg.warehouse", "s3://lakehouse/warehouse")
        .config("spark.sql.catalog.iceberg.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.iceberg.s3.endpoint", "http://minio:9000")
        .config("spark.sql.catalog.iceberg.s3.access-key-id", "minioadmin")
        .config("spark.sql.catalog.iceberg.s3.secret-access-key", "minioadmin")
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
    ]
    for table_name in table_names:
        path = GOLD_DIR / f"{table_name}.csv"
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(str(path))
        df.writeTo(f"iceberg.gold.{table_name}").using("iceberg").createOrReplace()
        print(f"wrote iceberg.gold.{table_name}: {df.count()} rows")

    spark.stop()


if __name__ == "__main__":
    main()
