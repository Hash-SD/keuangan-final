CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_organisasi (
    organisasi_key INTEGER,
    kode_unit VARCHAR,
    nama_fakultas VARCHAR,
    nama_prodi VARCHAR
);

CREATE TABLE IF NOT EXISTS gold.dim_mahasiswa (
    mahasiswa_key INTEGER,
    nim VARCHAR,
    nama_debitur VARCHAR
);

CREATE TABLE IF NOT EXISTS gold.dim_kualitas_piutang (
    kualitas_piutang_key INTEGER,
    kualitas VARCHAR,
    kriteria VARCHAR,
    persentase_penyisihan DOUBLE
);

CREATE TABLE IF NOT EXISTS gold.dim_waktu_tunggakan (
    waktu_tunggakan_key INTEGER,
    semester VARCHAR,
    tahun_akademik VARCHAR,
    tahun_anggaran VARCHAR,
    periode_key VARCHAR,
    umur_tunggakan INTEGER
);

CREATE TABLE IF NOT EXISTS gold.fact_piutang_ukt_prodi (
    piutang_key BIGINT,
    organisasi_key INTEGER,
    mahasiswa_key INTEGER,
    kualitas_piutang_key INTEGER,
    waktu_tunggakan_key INTEGER,
    dataset_session_id VARCHAR,
    tahun_akademik VARCHAR,
    tahun_anggaran VARCHAR,
    semester VARCHAR,
    periode_key VARCHAR,
    nominal_piutang_rp BIGINT,
    jumlah_mhs_penunggak INTEGER,
    source_filename VARCHAR,
    batch_id VARCHAR,
    created_at TIMESTAMP
);
