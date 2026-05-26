CREATE OR REPLACE VIEW gold.vw_dashboard_piutang_ukt AS
SELECT
    f.piutang_key,
    o.nama_fakultas,
    o.nama_prodi,
    m.nim,
    m.nama_debitur,
    k.kualitas,
    k.kriteria,
    k.persentase_penyisihan,
    w.semester,
    w.tahun_akademik,
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

