CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.fact_anggaran (
    item_id TEXT,
    dataset_session_id TEXT,
    run_id TEXT,
    tahun TEXT,
    prodi TEXT,
    fakultas TEXT,
    kegiatan TEXT,
    cluster_kegiatan TEXT,
    akun TEXT,
    kode_akun TEXT,
    nama_akun TEXT,
    nama_akun_asli TEXT,
    iku TEXT,
    kode_iku TEXT,
    nama_iku TEXT,
    nomenklatur_path TEXT,
    uraian_detail TEXT,
    qty DOUBLE PRECISION,
    satuan TEXT,
    harga_satuan DOUBLE PRECISION,
    jumlah DOUBLE PRECISION,
    allocation_weight DOUBLE PRECISION,
    jumlah_weighted_iku DOUBLE PRECISION,
    mapping_status TEXT,
    data_quality_flag TEXT,
    source_file TEXT,
    source_sheet TEXT,
    source_row INTEGER,
    source_role TEXT,
    row_type TEXT,
    quality_flags TEXT,
    created_at TIMESTAMPTZ
);

DROP VIEW IF EXISTS gold.vw_dashboard_iku_anggaran;
DROP VIEW IF EXISTS gold.vw_dashboard_mapping_quality;
DROP VIEW IF EXISTS gold.vw_dashboard_reconciliation;

ALTER TABLE gold.fact_anggaran DROP COLUMN IF EXISTS periode;
ALTER TABLE gold.fact_anggaran ADD COLUMN IF NOT EXISTS nama_akun_asli TEXT;
ALTER TABLE gold.fact_anggaran
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::TIMESTAMPTZ;

CREATE OR REPLACE VIEW gold.vw_dashboard_iku_anggaran AS
SELECT
    dataset_session_id,
    run_id,
    tahun,
    prodi,
    fakultas,
    kode_iku,
    nama_iku,
    iku,
    SUM(jumlah_weighted_iku) AS jumlah_weighted_iku
FROM gold.fact_anggaran
GROUP BY dataset_session_id, run_id, tahun, prodi, fakultas, kode_iku, nama_iku, iku;

CREATE OR REPLACE VIEW gold.vw_dashboard_mapping_quality AS
SELECT
    dataset_session_id,
    run_id,
    mapping_status,
    data_quality_flag,
    COUNT(*) AS item_count
FROM gold.fact_anggaran
GROUP BY dataset_session_id, run_id, mapping_status, data_quality_flag;

CREATE OR REPLACE VIEW gold.vw_dashboard_reconciliation AS
WITH item_level AS (
    SELECT
        dataset_session_id,
        run_id,
        tahun,
        source_file,
        item_id,
        MAX(jumlah) AS jumlah,
        SUM(jumlah_weighted_iku) AS jumlah_weighted_iku
    FROM gold.fact_anggaran
    GROUP BY dataset_session_id, run_id, tahun, source_file, item_id
)
SELECT
    source_file,
    SUM(jumlah) AS total_detail,
    SUM(jumlah_weighted_iku) AS total_rekap,
    SUM(jumlah) - SUM(jumlah_weighted_iku) AS selisih,
    CASE
        WHEN ABS(SUM(jumlah) - SUM(jumlah_weighted_iku)) <= 0.01 THEN 'OK'
        ELSE 'CHECK'
    END AS status,
    dataset_session_id,
    run_id,
    tahun
FROM item_level
GROUP BY source_file, dataset_session_id, run_id, tahun;
