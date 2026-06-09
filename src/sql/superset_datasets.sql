CREATE OR REPLACE VIEW gold.vw_dashboard_piutang_ukt AS
SELECT
    f.piutang_key,
    f.organisasi_key,
    f.mahasiswa_key,
    f.kualitas_piutang_key,
    f.waktu_tunggakan_key,
    f.dataset_session_id,
    COALESCE(f.tahun_akademik, w.tahun_akademik) AS tahun_akademik,
    COALESCE(f.tahun_anggaran, w.tahun_anggaran) AS tahun_anggaran,
    COALESCE(f.semester, w.semester) AS semester,
    COALESCE(f.periode_key, w.periode_key) AS periode_key,
    o.nama_fakultas,
    o.nama_prodi,
    o.kode_unit,
    m.nim,
    m.nama_debitur,
    k.kualitas,
    k.kriteria,
    k.persentase_penyisihan,
    w.umur_tunggakan,
    f.nominal_piutang_rp,
    f.jumlah_mhs_penunggak,
    f.source_filename,
    f.batch_id,
    f.created_at
FROM gold.fact_piutang_ukt_prodi f
JOIN gold.dim_organisasi o ON f.organisasi_key = o.organisasi_key
JOIN gold.dim_mahasiswa m ON f.mahasiswa_key = m.mahasiswa_key
JOIN gold.dim_kualitas_piutang k ON f.kualitas_piutang_key = k.kualitas_piutang_key
JOIN gold.dim_waktu_tunggakan w ON f.waktu_tunggakan_key = w.waktu_tunggakan_key;
