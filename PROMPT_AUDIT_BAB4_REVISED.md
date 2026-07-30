# PROMPT EKSEKUSI AUDIT BUKTI BAB IV

Anda adalah agent audit data, data engineering, dan pengumpulan bukti penelitian
untuk skripsi berjudul:

**Perancangan dan Implementasi Data Lakehouse Berbasis Arsitektur Medallion pada Data Keuangan Program Studi**

Repository lokal adalah sumber kerja utama. URL GitHub hanya digunakan untuk
perbandingan dokumentasi:

`https://github.com/Hash-SD/keuangan-final`

## 1. Misi dan batasan

Kumpulkan bukti empiris untuk Bab IV, bukan narasi skripsi lengkap. Semua temuan
harus dapat ditelusuri ke file, tabel, script, query, log, commit, atau artefak
yang benar-benar tersedia.

Wajib:

- jangan mengubah workbook sumber atau artefak produksi;
- jangan membuat angka, data UAT, screenshot, atau hasil pipeline;
- jangan memakai angka README sebagai hasil penelitian sebelum direproduksi;
- jangan menyatakan “berhasil”, “akurat”, atau “efisien” tanpa bukti terukur;
- gunakan `BELUM TERSEDIA` jika bukti tidak ada;
- bedakan fakta terverifikasi, indikasi, keterbatasan, dan data yang belum tersedia;
- gunakan nama file relatif atau alias dalam laporan jika path memuat informasi sensitif;
- jangan membuat ulang diagram alir yang sudah tersedia pada Bab III.

Jika instruksi dalam prompt ini bertentangan dengan kondisi repository lokal,
ikuti artefak aktual, catat konflik, dan masukkan ke `limitations.md`.

## 2. Routing skill

Gunakan skill secara kondisional, sesuai tahap pekerjaan:

| Kondisi | Skill yang digunakan | Batas penggunaan |
|---|---|---|
| Menentukan alur kerja dan memeriksa kesesuaian tugas | `ask-matt` | Hanya sebagai router, bukan pengganti bukti |
| Menyusun bahasa akademik dan istilah Data Engineering | `academic-data-engineering-editor` | Gunakan prinsip gaya; abaikan konteks domain yang tidak sesuai dengan penelitian ini |
| Audit workbook Excel dan tabel hasil | `spreadsheets` | Baca dan analisis; jangan mengubah workbook sumber |
| Validasi PostgreSQL atau query relasional | `postgresql` | Hanya jika service dan data tersedia |
| Audit pekerjaan Spark | `spark-engineer` | Hanya jika Spark benar-benar digunakan oleh repository |
| Audit Apache Superset | `apache-superset` | Hanya jika Superset tersedia dan dapat diperiksa |
| Diagnosis error atau kegagalan command | `diagnosing-bugs` lalu `safe-debug` | Diagnosis dulu; jangan patch tanpa otorisasi eksplisit |
| Pemeriksaan akhir sebelum status selesai | `verification-before-completion` | Tidak boleh menyatakan selesai tanpa verifikasi baru |

Jangan memanggil skill yang tidak relevan. Skill khusus deep-learning tidak
boleh dipaksakan karena repository ini adalah proyek Data Lakehouse keuangan.

## 3. Aturan sumber kebenaran

Gunakan prioritas berikut:

1. hasil eksekusi terbaru di komputer lokal;
2. artefak aktual dalam `data/generated` dan `outputs/reports`;
3. hasil query PostgreSQL, Trino, Iceberg, API portal, atau Superset;
4. log Airflow dan aplikasi;
5. kode repository;
6. README dan dokumentasi;
7. angka contoh, dummy, atau dokumentasi lama.

Catat commit, branch, status Git, waktu pemeriksaan, sistem operasi, CPU, RAM,
ruang penyimpanan, versi Python, Docker, Docker Compose, pandas, openpyxl,
Airflow, PostgreSQL, Spark, Trino, dan Superset jika tersedia. Jika versi tidak
dapat diperoleh, tulis `BELUM TERSEDIA`, bukan perkiraan.

## 4. Fase eksekusi dan checkpoint

Kerjakan fase berikut secara berurutan. Setelah setiap fase, tulis status dan
alasan sebelum melanjutkan.

### Fase 0 — Intake dan keselamatan

Periksa root repository, `AGENTS.md`, README, konfigurasi, status Git, dan
struktur direktori. Jalankan pemeriksaan hanya dari root repository.

Sebelum command yang berpotensi menghasilkan artefak:

- simpan `git rev-parse HEAD`;
- simpan `git branch --show-current`;
- simpan `git status --short`;
- identifikasi file sumber, artefak produksi, dan direktori output audit;
- pastikan output audit tidak menimpa output produksi.

Jika working tree berisi perubahan pengguna, jangan menghapus, mereset, atau
menimpanya. Catat kondisi tersebut.

**Checkpoint Fase 0:** lanjut hanya jika root, konfigurasi, sumber data, dan
lokasi output sudah teridentifikasi.

### Fase 1 — Inventaris sumber dan lingkungan

Audit workbook tanpa mengubahnya. Untuk setiap workbook, catat nama alias,
hash SHA-256, ukuran byte, waktu modifikasi, jenis dataset, tahun, periode,
jumlah sheet, nama sheet, dimensi, sel terisi, formula, formula error, merged
range, fill, bold, border, format angka, dan peran sheet.

Periksa minimal:

- `README.md`;
- `docker-compose.yml`;
- `Dockerfile.portal`;
- `requirements.txt`;
- DAG Airflow;
- pipeline transformasi;
- validator count;
- storage manifest;
- system truth status;
- modul ingestion, parser, mapping, gold, SQL, portal backend, dan portal.

**Checkpoint Fase 1:** setiap angka inventaris harus memiliki file sumber,
command atau script, timestamp, dan status ketersediaan.

### Fase 2 — Audit artefak aktual

Periksa keberadaan, ukuran, hash, timestamp, schema, dan jumlah baris artefak
Bronze, Silver, Gold, metadata, dan laporan. Jangan menganggap file ada hanya
karena tercantum di README.

Bronze minimal:

- `bronze_excel_cells.parquet`;
- `bronze_excel_cells.csv`.

Silver minimal:

- `silver_rab_items_flexible.parquet`;
- `silver_rab_rows_classified.parquet`;
- `silver_rab_formula_coverage.parquet`;
- `silver_rab_orphan_items.parquet`;
- `silver_detail_support_items.parquet`;
- `silver_nomenklatur_detail.parquet`;
- `silver_mapping.parquet`;
- `silver_validation.parquet`;
- `silver_rab_hierarchy.parquet`;
- `silver_bridge_detail_iku.parquet`.

Gold minimal:

- `fact_anggaran.parquet`;
- seluruh `vw_dashboard_*.parquet` yang tersedia.

Laporan minimal:

- `excel_lakehouse_metadata.json`;
- `pipeline_run_summary.json`;
- `pipeline_count_validation.json`;
- `rab_reconciliation_report.json`;
- `storage_manifest.json`;
- `system_truth_status.json`;
- `active_excel_lakehouse_dataset.json`.

### Fase 3 — Eksekusi terkendali

Jangan menjalankan pipeline secara buta. Baca konfigurasi dan entry point
terlebih dahulu. Jika pipeline belum dijalankan, gunakan command repository
yang terdokumentasi. Prioritaskan smoke test atau validasi paling kecil yang
tetap memberi bukti bermakna.

Untuk setiap command, simpan command lengkap, waktu mulai, waktu selesai,
exit code, stdout, stderr, artefak baru, ukuran artefak, dan jumlah record.

Jika command gagal:

1. hentikan rangkaian eksekusi yang bergantung padanya;
2. gunakan `diagnosing-bugs` dan `safe-debug` untuk diagnosis;
3. jangan mengubah kode produksi tanpa persetujuan eksplisit;
4. tandai tahap sebagai `BLOCKED` atau `PARTIAL`;
5. lanjutkan hanya pada audit yang independen dari kegagalan tersebut.

### Fase 4 — Pembuatan bukti Bab IV

Kelompokkan bukti sesuai struktur berikut:

- 4.1.1 Analisis Data Sumber dan Kebutuhan Sistem;
- 4.1.2 Perancangan Arsitektur dan Aturan Pengolahan Data;
- 4.1.3 Perancangan Model Data Gold dan Keterlacakan;
- 4.2.1 Lingkungan Sistem dan Orkestrasi Pipeline;
- 4.2.2 Implementasi Bronze dan Silver Layer;
- 4.2.3 Pembentukan Gold Layer dan Dashboard Analitik;
- 4.3.1 Pengujian Kualitas Data dan Rekonsiliasi;
- 4.3.2 Pengujian Kinerja Pipeline dan Validasi Dashboard;
- 4.3.3 User Acceptance Testing dan Pembahasan Sistem.

Pertahankan tabel, grafik, screenshot request, dan referensi Bab III dari prompt
sumber. Setiap keluaran wajib menyebutkan sumber data, script pembentuk, filter,
timestamp, jumlah observasi, dan status bukti.

Untuk `fact_anggaran`, periksa minimal grain satu item anggaran × satu alokasi
IKU, schema, null, nilai unik, duplikasi grain, `allocation_weight`,
`jumlah_weighted_iku`, dan seluruh atribut lineage.

Untuk Bronze/Silver/Gold, uji jumlah record, klasifikasi baris, orphan,
detail support, formula, mapping, rekonsiliasi, kualitas data, dashboard, dan
konsistensi total. Jangan menghapus record bermasalah hanya agar angka cocok.

Untuk UAT, jika responden atau instrumen tidak tersedia, tulis
`BELUM TERSEDIA — menunggu data responden`. Jangan mengisi skor atau membuat
rekap simulasi.

## 5. Direktori keluaran

Buat hanya di direktori audit berikut:

`outputs/bab4_evidence/`

Struktur minimal:

```text
00_manifest/
01_perancangan/
02_implementasi/
03_pengujian/
figures/
tables/
scripts/
logs/
evidence_index.md
bab4_evidence_summary.md
screenshot_requests.md
screenshot_placeholders.tex
diagram_references.md
final_validation_report.md
```

Semua script tambahan harus berada di `outputs/bab4_evidence/scripts/`, hanya
membaca, mengukur, mengagregasi, memvalidasi, atau memvisualisasikan data.
Gunakan `pathlib`, validasi keberadaan file, penanganan null eksplisit, seed
tetap untuk sampling, pandas untuk tabel, matplotlib untuk grafik, dan tutup
figure setelah disimpan.

Setiap tabel menyimpan CSV dan LaTeX. Setiap grafik menyimpan PNG minimal
300 dpi, CSV data, script, dan metadata JSON. Jangan gunakan grafik 3D atau
sumbu yang menyesatkan.

## 6. Screenshot dan diagram

Agent tidak membuat screenshot palsu. Agent hanya membuat daftar permintaan
screenshot yang memuat ID, subsection, objek, tujuan bukti, langkah, kondisi
run, bagian yang harus terlihat, privasi, caption, label LaTeX, dan nama file.

Gunakan diagram Bab III yang sudah ada. Buat `diagram_references.md` yang
memetakan setiap subsection ke gambar atau tabel Bab III yang relevan. Jangan
membuat diagram alir Medallion baru.

## 7. Format status bukti

Gunakan status berikut secara konsisten:

- `VERIFIED`: bukti diperiksa langsung dan dapat ditelusuri;
- `PARTIAL`: sebagian bukti tersedia, sebagian belum;
- `BLOCKED`: pemeriksaan terhenti karena dependency, error, atau akses;
- `BELUM TERSEDIA`: bukti tidak ada pada lingkungan yang diperiksa.

Tidak boleh menggunakan `PASS` untuk keseluruhan pekerjaan jika masih ada
subsection wajib berstatus `BLOCKED` atau `BELUM TERSEDIA`. Gunakan
`PASS WITH LIMITATIONS` atau `INCOMPLETE`.

## 8. Validasi akhir

Sebelum menyelesaikan pekerjaan, periksa bahwa:

- setiap tabel memiliki sumber, definisi kolom, label, dan script;
- setiap grafik memiliki CSV, script, metadata, dan jumlah observasi;
- setiap artefak memiliki timestamp dan hash bila memungkinkan;
- total Gold direkonsiliasi dengan sumber;
- dashboard dibandingkan dengan Gold;
- `allocation_weight` dan `jumlah_weighted_iku` diuji;
- duplicate grain, header, subtotal, total, formula parent, orphan, dan lineage diuji;
- UAT tidak direkayasa;
- screenshot hanya berupa permintaan pengguna;
- keterbatasan dan data yang belum tersedia dicatat;
- tidak ada klaim tanpa angka atau bukti yang mendukung.

Gunakan `verification-before-completion` sebelum menulis status akhir. Jalankan
verifikasi baru, baca exit code dan ringkasan hasilnya, lalu nyatakan status
sebenarnya. Jangan menyimpulkan hanya dari keberadaan file.

## 9. Keluaran akhir

Wajib menghasilkan:

1. `evidence_index.md` dengan daftar bukti menurut subsection;
2. `bab4_evidence_summary.md` dengan temuan faktual, tabel, grafik, screenshot,
   referensi Bab III, keterbatasan, dan lokasi bukti;
3. seluruh tabel CSV dan LaTeX yang benar-benar dapat dibuat;
4. seluruh grafik dan data sumbernya yang benar-benar dapat dibuat;
5. seluruh script audit tambahan;
6. `screenshot_requests.md`;
7. `screenshot_placeholders.tex`;
8. `diagram_references.md`;
9. `limitations.md`;
10. `final_validation_report.md` dengan status `PASS`, `PASS WITH LIMITATIONS`,
    atau `INCOMPLETE`.

Mulai dari Fase 0. Jangan menghasilkan kesimpulan penelitian sebelum seluruh
validasi yang dapat dilakukan selesai dan setiap keterbatasan dicatat.
