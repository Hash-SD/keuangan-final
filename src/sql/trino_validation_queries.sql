SELECT
    o.nama_prodi,
    w.tahun_akademik,
    SUM(nominal_piutang_rp) AS total_piutang,
    COUNT(*) AS jumlah_penunggak
FROM gold.fact_piutang_ukt_prodi f
JOIN gold.dim_organisasi o
    ON f.organisasi_key = o.organisasi_key
JOIN gold.dim_waktu_tunggakan w
    ON f.waktu_tunggakan_key = w.waktu_tunggakan_key
WHERE o.nama_prodi = 'Sains Data'
GROUP BY o.nama_prodi, w.tahun_akademik
ORDER BY w.tahun_akademik;
