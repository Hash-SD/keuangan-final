# Brainstorming Plan - Revisi Excel Lakehouse Keuangan Prodi

Tanggal: 2026-06-29

## 1. Ringkasan Pemahaman Sistem Lama

Sistem lama sudah memiliki stack platform yang harus dipertahankan: Docker Compose, Airflow, Spark, MinIO, PostgreSQL metastore, Iceberg, Trino, Superset, portal frontend, dan portal backend. Masalah utamanya ada di domain pipeline: pipeline lama masih dominan membaca PDF audited, CSV transaksi, dummy piutang UKT, dan RAB dummy sederhana.

Pipeline baru harus mengubah domain menjadi Excel-only untuk RAB, RPD, IKU, dan Nomenklatur. Rebuild dari nol tidak diperlukan; modul platform dipertahankan, sedangkan modul domain ekstraksi/transformasi/gold/dashboard diganti bertahap.

Audit detail: `docs/brainstorming/repo_audit.md`.

## 2. Ringkasan Pemahaman File Excel 2023

RAB 2023 terdiri dari dua workbook periode:

- `RAB_SD_Usulan KE (1)_Jan-Jun 2023.xlsx`
- `RAB_SD_Usulan KE (1)_jul-des 2023.xlsx`

Keduanya harus diproses sebagai satu tahun anggaran 2023. Sheet penting:

- `REKAP` untuk kontrol total.
- `Prioritas Kegiatan` untuk konteks kegiatan dan IKU.
- Sheet akun belanja untuk item detail.

Parser 2023 harus membaca konteks `Kegiatan :`, header detail (`Uraian`, `QTY`, `Harga`, `Total/Jumlah`), kode akun dari nama sheet atau baris, lalu menggabungkan Jan-Jun dan Jul-Des tanpa overwrite.

## 3. Ringkasan Pemahaman File Excel 2024

RAB 2024 memiliki format legacy yang lebih bebas. Sheet penting:

- `REKAP` untuk total akun.
- `USULAN PROKER SD` untuk program kerja dan mapping IKU.
- Sheet kegiatan seperti `PKS`, `SG & Kuliah Tamu`, `Belanja ATK`, `Sertifikasi Spark`, dan lain-lain.

Parser 2024 harus membaca sheet detail sebagai konteks kegiatan, mengenali blok warna lokal, mempertahankan source row/sheet, dan membuat validasi detail vs rekap. Perbedaan total tidak langsung dianggap fatal; hasilnya masuk `silver_validation` dengan status review.

## 4. Ringkasan Pemahaman File Excel 2025

RAB 2025 adalah template paling stabil. Sheet penting:

- `RAB` dan `RPD` sebagai struktur anggaran/RPD berbasis warna.
- `master akun`, `master IKU`, `ket_akun` sebagai referensi.
- Sheet rincian akun dan rekap sebagai audit.

Parser 2025 tidak boleh memakai `pandas.read_excel()` flat saja karena konteks berasal dari warna, merge, posisi, formula, dan baris sebelumnya. `openpyxl` diperlukan untuk membaca metadata visual.

## 5. Ringkasan Pemahaman Nomenklatur

Nomenklatur adalah master kegiatan/IKU. Sheet `Nomenklatur FS` memakai kolom B-F dan warna sebagai level:

- Kegiatan
- KRO
- RO
- Komponen
- Sub Komponen
- Detail Kegiatan

Silver Nomenklatur harus menghasilkan satu baris per detail kegiatan dengan parent lengkap, `nomenklatur_path`, `nomenklatur_key`, dan bridge IKU dengan `allocation_weight = 1/n`.

## 6. Skill Discovery

Perintah yang dijalankan:

```powershell
npx skills add https://github.com/vercel-labs/skills --skill find-skills
npx skills find "Excel parsing openpyxl data validation" --json
npx skills find "Airflow Spark PySpark data pipeline medallion" --json
npx skills find "Superset dashboard Trino Iceberg Docker PostgreSQL" --json
npx skills find "repository refactor testing documentation UI UX portal" --json
```

Skill yang ditemukan dari registry:

| Skill | Alasan dipertimbangkan | Bagian pipeline | Risiko jika tidak digunakan |
| --- | --- | --- | --- |
| `vasilyu1983/ai-agents-public@document-xlsx` | Relevan untuk workbook Excel, 663 installs | Profiling/authoring Excel | Analisis Excel bisa kurang mengikuti pola workbook, tetapi skill lokal `spreadsheets` sudah lebih sesuai dalam sesi ini |
| `404kidwiz/claude-supercode-skills@xlsx` | Relevan untuk XLSX, 106 installs | Parsing workbook | Install count relatif rendah, sehingga tidak dijadikan fondasi utama |
| `vamseeachanta/workspace-hub@openpyxl` | Relevan langsung dengan openpyxl, 38 installs | Bronze extractor | Install count rendah; lebih aman memakai dokumentasi resmi via Context7 |
| `aradotso/data-skills@retail-etl-medallion-pipeline` | Relevan Medallion, 609 installs | Desain Bronze/Silver/Gold | Domain retail, perlu adaptasi besar |
| `microsoft/skills-for-fabric@e2e-medallion-architecture` | Sumber reputasi baik untuk Medallion, 96 installs | Arsitektur | Install count di bawah 100, dipakai sebagai inspirasi saja bila diinstall nanti |
| `manutej/luxor-claude-marketplace@apache-spark-data-processing` | Relevan Spark, 256 installs | Spark transform/load | Skill lokal `spark-engineer` sudah tersedia dan lebih langsung |
| `vasilyu1983/ai-agents-public@data-lake-platform` | Relevan lake platform, 127 installs | Platform integration | Tidak spesifik stack repo |
| `thebushidocollective/han@monorepo-architecture` | Relevan audit/refactor repo, 58 installs | Repo cleanup | Install count rendah; audit dilakukan dengan skill lokal `repo-cleanup` bila fase cleanup dimulai |
| `williamfontaine/claude-plugins-marketplace@ux-admin-portal` | Relevan portal UI admin, 19 installs | Portal UI/UX | Terlalu rendah untuk jadi acuan utama |

Skill lokal yang digunakan karena sudah tersedia:

| Skill lokal | Kenapa dipakai | Bagian pipeline | Risiko jika tidak digunakan |
| --- | --- | --- | --- |
| `find-skills` | Wajib untuk discovery | Perencanaan | Bisa salah memilih kemampuan pendukung |
| `spreadsheets:Spreadsheets` | Wajib untuk analisis workbook Excel | Dataset profiling dan validasi workbook | Parser bisa mengabaikan formula/style/format |
| `airflow-dag-patterns` | Desain DAG idempotent | Airflow DAG baru | DAG rawan retry tidak aman |
| `spark-engineer` | Spark/Iceberg transform/load | Silver/Gold skala besar | Transformasi bisa tidak efisien atau sulit dipublish |
| `repo-cleanup` | Fase cleanup aman | Legacy marking/remove later | Berisiko menghapus kode lama terlalu cepat |
| `frontend-js-best-practices` dan `frontend-tailwind-best-practices` | Fase portal | Upload/status UI | UI bisa berat dan tidak konsisten |
| `a11y-audit` | Fase portal | Aksesibilitas UI | Portal sulit dipakai dan rawan regresi WCAG |

## 7. MCP yang Digunakan

- Context7 MCP untuk dokumentasi resmi `openpyxl` dan Airflow.
- Context7 `openpyxl` mengonfirmasi `load_workbook(..., data_only=False)` untuk formula dan style, serta `data_only=True` untuk nilai formula terakhir.
- Context7 Airflow mengonfirmasi TaskFlow API sebagai pola modern, tetapi migrasi awal tetap boleh memakai BashOperator karena repo lama sudah berbasis script containerized.
- GitHub/Docker/PostgreSQL/Superset MCP belum digunakan karena tool spesifik belum tersedia/ belum diperlukan pada tahap discovery ini.

## 8. Bagian Sistem Lama yang Dipertahankan

- Docker Compose dan service platform.
- Konfigurasi Airflow/Spark/Trino/Superset.
- Portal shell dan backend service skeleton.
- Utilitas runtime config/path/logging.
- Storage manifest.
- Test lama sebagai guard sampai test domain baru lengkap.

## 9. Bagian Sistem Lama yang Diganti

- PDF extraction menjadi legacy.
- Piutang UKT sebagai mart utama diganti `fact_anggaran`.
- Parser RAB rigid berbasis `pd.read_excel(sheet_name="RAB")` diganti parser openpyxl cell/context/color.
- Superset dashboard piutang diganti dashboard IKU/anggaran.
- Upload PDF/CSV diganti upload Excel multi-file dengan metadata dataset.

## 10. Risiko Teknis

- File Excel memakai format visual, warna, dan merge; parser flat akan gagal.
- Tahun dari isi workbook bisa ambigu karena ada referensi 2023/2024/2025 dalam satu sheet.
- 2023 wajib multi-file; jika salah merge total tahunan salah.
- 2024 memiliki selisih detail vs rekap yang harus ditandai review, bukan dipaksa OK.
- Nomenklatur punya warna tambahan di luar mapping utama.
- Gold single fact table rawan double-count IKU jika item dengan banyak IKU tidak diberi allocation weight.
- Portal/test lama masih bergantung pada PDF; cleanup harus bertahap.

## 11. Strategi Implementasi Bertahap

Tahap 1 - Discovery:

- Install dan baca `find-skills`.
- Baca semua markdown requirement.
- Profiling semua workbook contoh.
- Audit repo lama.

Tahap 2 - Foundation:

- Buat `src/excel_ingestion/`.
- Buat extractor cell-level.
- Simpan output Bronze CSV/Parquet.
- Buat dataset profile reports.

Tahap 3 - Parser:

- Buat `src/parser_flexible/year_detector.py`.
- Buat `src/parser_flexible/sheet_detector.py`.
- Buat parser Nomenklatur.
- Buat parser RAB 2025-like.
- Buat parser legacy 2024.
- Buat parser legacy 2023 multi-file.

Tahap 4 - Silver:

- Merge multi-file per tahun.
- Normalisasi item ke kolom logika yang sama.
- Mapping akun, kegiatan, IKU, nomenklatur.
- Validasi total detail vs rekap.

Tahap 5 - Gold:

- Buat `fact_anggaran`.
- Hitung `allocation_weight` dan `jumlah_weighted_iku`.
- Buat view dashboard.

Tahap 6 - Platform Integration:

- Buat DAG baru `keuangan_prodi_excel_lakehouse_dag`.
- Publish Gold ke Postgres/Iceberg.
- Refresh Superset dataset/dashboard.
- Update status API.

Tahap 7 - Portal:

- Upload Excel-only.
- Dataset registry.
- Pipeline status.
- Data quality.
- Dashboard links.

Tahap 8 - QA dan Cleanup:

- Tambah unit/integration tests.
- Jalankan sample-run lima workbook.
- Tandai modul lama sebagai legacy.
- Hapus PDF hanya setelah tidak direferensikan.

## 12. Strategi Testing

Test wajib:

- `tests/test_bronze_excel_cells.py`
- `tests/test_parse_2023.py`
- `tests/test_parse_2024.py`
- `tests/test_parse_2025.py`
- `tests/test_parse_nomenklatur.py`
- `tests/test_fact_anggaran.py`
- `tests/test_multi_file_merge.py`
- `tests/test_iku_allocation.py`

Acceptance minimum:

- Semua workbook contoh bisa diekstrak.
- Bronze menyimpan value, formula, warna, merge, source lineage.
- 2023 Jan-Jun dan Jul-Des tergabung.
- Silver mempertahankan source file/sheet/row.
- `fact_anggaran` terbentuk.
- `jumlah_weighted_iku` tidak double-count.
- Parser tidak bergantung penuh pada nama file.

## 13. Output Final yang Diharapkan

- `docs/brainstorming/revisi_excel_lakehouse_plan.md`
- `docs/brainstorming/repo_audit.md`
- `docs/brainstorming/dataset_profile_summary.md`
- `src/excel_ingestion/`
- `src/parser_flexible/`
- `src/mapping/`
- `src/gold/`
- `dags/keuangan_prodi_excel_lakehouse_dag.py`
- `data/generated/bronze/bronze_excel_cells.parquet`
- `data/generated/silver/silver_rab_items_flexible.parquet`
- `data/generated/silver/silver_nomenklatur_detail.parquet`
- `data/generated/gold/fact_anggaran.parquet`
- `outputs/reports/system_truth_status.json`
- `outputs/reports/dataset_profile_*.json`
- `outputs/reports/pipeline_run_summary.json`
- Test suite baru untuk pipeline Excel.

## 14. Keputusan Desain

- Parser awal memakai Python `openpyxl`, bukan Spark, karena Spark tidak ideal untuk membaca style Excel.
- Spark dipakai setelah data menjadi tabular Bronze/Silver.
- Gold mengikuti PRD terbaru: single fact table `fact_anggaran`.
- Bridge IKU secara fisik boleh ada di Silver untuk audit, tetapi dashboard utama memakai `allocation_weight` dan `jumlah_weighted_iku` di `fact_anggaran`.
- Nama file hanya sinyal pendukung; metadata upload dan isi workbook menjadi sumber deteksi utama.
