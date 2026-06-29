# Repository Audit - Excel Lakehouse Redesign

Tanggal audit: 2026-06-29

## Ringkasan

Repository `keuangan-final` sudah memiliki platform lakehouse lokal yang cukup lengkap: Docker Compose, Airflow, MinIO, PostgreSQL metastore, Trino, Superset, portal frontend, portal backend, generator dummy, status API, dan test suite. Yang perlu diganti bukan platformnya, melainkan domain pipeline yang saat ini masih berpusat pada piutang UKT, CSV transaksi, PDF audited, dan RAB dummy sederhana.

## KEEP

- `docker-compose.yml`: tetap menjadi orkestrasi stack lokal.
- `config/airflow`, `config/spark`, `config/trino`, `config/superset`: dipertahankan sebagai konfigurasi platform.
- `portal/` dan `portal_backend/`: shell UI/API dipertahankan, domain upload dan status perlu diubah bertahap.
- `src/common/`: utilitas path, runtime config, logging, waktu, dan pointer dataset masih berguna.
- `src/storage/`: manifest dan MinIO integration dipertahankan, perlu perluasan untuk Bronze/Silver/Gold Excel.
- `tests/`: test lama tetap dipakai sebagai guard platform sampai domain baru punya test lengkap.

## MODIFY

- `dags/`: tambahkan DAG baru `keuangan_prodi_excel_lakehouse_dag.py`; DAG lama tetap ada sebagai legacy sampai migrasi aman.
- `src/sql/load_gold_to_postgres.py`: perlu mengenali `fact_anggaran`.
- `src/transformations/load_gold_iceberg.py`: perlu publish `fact_anggaran` jika tersedia.
- `src/status/system_truth_status.py`: perlu status baru untuk Excel-only Bronze, Silver, Gold, dan dashboard IKU.
- `src/sql/setup_superset_assets.py` dan `src/sql/setup_superset_dashboard.py`: perlu dataset/chart dari `fact_anggaran`.
- `portal_backend/services/upload_session.py`: perlu upload Excel multi-file dan metadata `tahun_input`, `periode`, `prodi`, `fakultas`, `jenis_dataset`, `catatan`.
- `portal/index.html`: perlu halaman upload Excel-only, registry dataset, pipeline status, data quality, dashboard links.

## REPLACE

- Domain transformasi di `src/transformations/silver_clean.py` untuk RAB: pembacaan `pd.read_excel(sheet_name="RAB")` terlalu rigid dan harus diganti jalur parser fleksibel.
- Gold domain piutang sebagai mart utama di `src/transformations/gold_star_schema.py`: tetap sementara, tetapi mart utama baru adalah `fact_anggaran`.
- Superset dashboard piutang sebagai dashboard utama: diganti dashboard IKU/anggaran berbasis `fact_anggaran`.

## LEGACY

- `src/extraction/extract_pdf_piutang.py`: legacy karena PRD baru Excel-only dan tidak memakai PDF.
- `src/generators/generate_pdf_audited.py`: legacy untuk pipeline baru.
- `data/raw_lama/pdf` dan sample PDF: legacy, tidak dihapus dulu karena masih dipakai test lama.
- Tests piutang/PDF: legacy guard, bukan acceptance utama pipeline baru.

## REMOVE_LATER

- Dependency PDF (`pdfplumber`, `pypdf`, `reportlab`) setelah test dan UI lama tidak lagi bergantung padanya.
- Endpoint `/api/pdf/sample-status` setelah portal baru stabil.
- Dokumentasi checkpoint lama yang menyatakan PDF sebagai sumber utama, setelah dokumen migrasi baru lengkap.

## DO_NOT_TOUCH

- `.git/`, `.env`, `.env.example` kecuali ada kebutuhan eksplisit.
- Data user di `D:\Downloads`.
- File generated lama yang masih dibutuhkan test sampai pipeline baru menggantikannya.

## Migration Map

1. Tambah modul baru tanpa menghapus modul lama.
2. Buat Bronze Excel cell-level.
3. Buat parser fleksibel RAB/Nomenklatur.
4. Bangun Silver normalisasi dan validation.
5. Bangun `fact_anggaran` single fact table.
6. Tambah DAG baru dan publish ke Postgres/Iceberg.
7. Tambah Superset dataset/dashboard baru.
8. Ubah portal menjadi Excel-only.
9. Setelah test baru hijau, tandai pipeline PDF/piutang sebagai legacy.
10. Cleanup hanya setelah tidak ada referensi aktif.
