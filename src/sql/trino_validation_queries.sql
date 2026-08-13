SELECT COUNT(*) AS fact_anggaran_rows
FROM gold.fact_anggaran;

SELECT
    tahun,
    COUNT(*) AS item_count,
    SUM(jumlah) AS total_anggaran,
    SUM(jumlah_weighted_iku) AS total_anggaran
FROM gold.fact_anggaran
GROUP BY tahun
ORDER BY tahun;

SELECT
    kode_iku,
    nama_iku,
    SUM(jumlah_weighted_iku) AS total_anggaran
FROM gold.fact_anggaran
GROUP BY kode_iku, nama_iku
ORDER BY kode_iku;

SELECT
    data_quality_flag,
    COUNT(*) AS item_count
FROM gold.fact_anggaran
GROUP BY data_quality_flag
ORDER BY data_quality_flag;
