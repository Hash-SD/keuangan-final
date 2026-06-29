CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.fact_anggaran (
    item_id TEXT,
    run_id TEXT,
    tahun TEXT,
    periode TEXT,
    prodi TEXT,
    fakultas TEXT,
    kegiatan TEXT,
    cluster_kegiatan TEXT,
    akun TEXT,
    kode_akun TEXT,
    nama_akun TEXT,
    iku TEXT,
    kode_iku TEXT,
    nama_iku TEXT,
    nomenklatur_path TEXT,
    uraian_detail TEXT,
    qty DOUBLE PRECISION,
    satuan TEXT,
    harga_satuan DOUBLE PRECISION,
    jumlah DOUBLE PRECISION,
    jumlah_weighted_iku DOUBLE PRECISION,
    allocation_weight DOUBLE PRECISION,
    mapping_status TEXT,
    data_quality_flag TEXT,
    source_file TEXT,
    source_sheet TEXT,
    source_row INTEGER,
    created_at TIMESTAMP
);

CREATE OR REPLACE VIEW gold.vw_dashboard_iku_anggaran AS
SELECT
    run_id,
    tahun,
    periode,
    prodi,
    fakultas,
    kode_iku,
    nama_iku,
    iku,
    SUM(jumlah_weighted_iku) AS jumlah_weighted_iku
FROM gold.fact_anggaran
GROUP BY run_id, tahun, periode, prodi, fakultas, kode_iku, nama_iku, iku;

CREATE OR REPLACE VIEW gold.vw_dashboard_mapping_quality AS
SELECT
    run_id,
    mapping_status,
    data_quality_flag,
    COUNT(*) AS item_count
FROM gold.fact_anggaran
GROUP BY run_id, mapping_status, data_quality_flag;

CREATE OR REPLACE VIEW gold.vw_dashboard_reconciliation AS
SELECT
    source_file,
    SUM(jumlah) AS total_detail,
    SUM(jumlah_weighted_iku) AS total_weighted_iku,
    SUM(jumlah) - SUM(jumlah_weighted_iku) AS selisih_weighted,
    CASE
        WHEN ABS(SUM(jumlah) - SUM(jumlah_weighted_iku)) < 1 THEN 'OK'
        ELSE 'CHECK'
    END AS validation_status
FROM gold.fact_anggaran
GROUP BY source_file;
