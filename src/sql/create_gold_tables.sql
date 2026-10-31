CREATE SCHEMA IF NOT EXISTS gold;

-- Tabel dimensi star schema
CREATE TABLE IF NOT EXISTS gold.dim_organisasi (
    org_key SERIAL PRIMARY KEY,
    prodi TEXT NOT NULL,
    fakultas TEXT,
    UNIQUE (prodi, fakultas)
);

CREATE TABLE IF NOT EXISTS gold.dim_kegiatan (
    kegiatan_key SERIAL PRIMARY KEY,
    kegiatan TEXT NOT NULL,
    cluster_kegiatan TEXT,
    nomenklatur_path TEXT,
    UNIQUE (kegiatan, cluster_kegiatan, nomenklatur_path)
);

CREATE TABLE IF NOT EXISTS gold.dim_akun (
    akun_key SERIAL PRIMARY KEY,
    kode_akun TEXT,
    nama_akun TEXT,
    akun TEXT,
    nama_akun_asli TEXT,
    UNIQUE (kode_akun, nama_akun, akun, nama_akun_asli)
);

CREATE TABLE IF NOT EXISTS gold.dim_iku (
    iku_key SERIAL PRIMARY KEY,
    kode_iku TEXT UNIQUE NOT NULL,
    iku TEXT,
    nama_iku TEXT
);

-- Tabel fact star schema
CREATE TABLE IF NOT EXISTS gold.fact_anggaran (
    fact_key SERIAL PRIMARY KEY,
    item_id TEXT NOT NULL,
    dataset_session_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    tahun TEXT NOT NULL,
    org_key INTEGER REFERENCES gold.dim_organisasi (org_key),
    kegiatan_key INTEGER REFERENCES gold.dim_kegiatan (kegiatan_key),
    akun_key INTEGER REFERENCES gold.dim_akun (akun_key),
    iku_key INTEGER REFERENCES gold.dim_iku (iku_key),
    uraian_detail TEXT,
    satuan TEXT,
    qty DOUBLE PRECISION,
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
FROM gold.vw_fact_anggaran
GROUP BY dataset_session_id, run_id, tahun, prodi, fakultas, kode_iku, nama_iku, iku;

CREATE OR REPLACE VIEW gold.vw_dashboard_mapping_quality AS
SELECT
    dataset_session_id,
    run_id,
    mapping_status,
    data_quality_flag,
    COUNT(*) AS item_count
FROM gold.vw_fact_anggaran
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
    FROM gold.vw_fact_anggaran
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

CREATE OR REPLACE VIEW gold.vw_fact_anggaran AS
SELECT
    f.item_id,
    f.dataset_session_id,
    f.run_id,
    f.tahun,
    o.prodi,
    o.fakultas,
    k.kegiatan,
    k.cluster_kegiatan,
    a.akun,
    a.kode_akun,
    a.nama_akun,
    a.nama_akun_asli,
    i.iku,
    i.kode_iku,
    i.nama_iku,
    k.nomenklatur_path,
    f.uraian_detail,
    f.qty,
    f.satuan,
    f.harga_satuan,
    f.jumlah,
    f.allocation_weight,
    f.jumlah_weighted_iku,
    f.mapping_status,
    f.data_quality_flag,
    f.source_file,
    f.source_sheet,
    f.source_row,
    f.source_role,
    f.row_type,
    f.quality_flags,
    f.created_at
FROM gold.fact_anggaran f
LEFT JOIN gold.dim_organisasi o ON f.org_key = o.org_key
LEFT JOIN gold.dim_kegiatan k ON f.kegiatan_key = k.kegiatan_key
LEFT JOIN gold.dim_akun a ON f.akun_key = a.akun_key
LEFT JOIN gold.dim_iku i ON f.iku_key = i.iku_key;
