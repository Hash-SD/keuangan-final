# CHECKPOINT-07: Trino dan Superset

## Ringkasan

Trino dan Superset berjalan di Docker. Trino berhasil membaca Gold mart melalui catalog `iceberg`. Superset service healthy dan dataset diarahkan ke koneksi Trino Iceberg.

## File Dibuat/Diubah

- `config/trino/catalog/iceberg.properties`
- `config/trino/catalog/postgres.properties`
- `config/superset/superset_config.py`
- `src/sql/superset_datasets.sql`
- `src/sql/setup_superset_assets.py`
- `outputs/reports/superset_assets.json`

## Command Dijalankan

```powershell
docker compose up -d
docker compose ps
docker exec keuangan-trino trino --execute "SHOW CATALOGS"
docker exec keuangan-trino trino --catalog iceberg --schema gold --execute "SELECT SUM(nominal_piutang_rp) AS total_piutang, COUNT(*) AS jumlah_penunggak FROM fact_piutang_ukt_prodi f JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key WHERE o.nama_prodi = 'Sains Data'"
python src/sql/setup_superset_assets.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_ports.ps1
```

## Status Validasi

- Trino healthy di http://localhost:8082.
- Superset healthy di http://localhost:8089.
- Catalog Trino tersedia: `iceberg`, `postgres`, `system`.
- Query validasi Trino Iceberg menghasilkan `"31250000","15"`.
- Superset database connection dibuat: `Trino Iceberg Gold Keuangan`.
- Superset dataset dibuat: `vw_dashboard_piutang_ukt`.
- Semua port lokal tervalidasi OK.

## Catatan Dashboard

Superset login: `admin` / `admin`.

Koneksi database yang digunakan:

```text
trino://trino@trino:8080/iceberg/gold
```

Dataset utama sudah dibuat via API:

```text
iceberg.gold.vw_dashboard_piutang_ukt
```

Chart yang harus dibuat mengikuti `end_to_end_plan_data_lakehouse_mcp_skills.md`: Big Number total piutang, Big Number jumlah penunggak, bar chart per prodi, distribusi kualitas, tren semester, tabel rincian, dan native filters.

## Langkah Berikutnya

CHECKPOINT-08 Testing dan Evaluasi.
