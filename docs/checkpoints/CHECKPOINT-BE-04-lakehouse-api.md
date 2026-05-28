# CHECKPOINT-BE-04: Lakehouse API

## Tujuan
Mengecek status Bronze, Silver, Gold, dan validasi Gold dari file output lokal.

## File Dibaca
- data/generated/bronze/ingestion_metadata.json
- data/generated/silver/fact_piutang_ukt_prodi.csv
- data/generated/silver/transactions_clean.csv
- data/generated/silver/rab_prodi_sains_data_long.csv
- data/generated/gold/fact_piutang_ukt_prodi.csv
- data/generated/gold/vw_dashboard_piutang_ukt.csv
- outputs/metrics/reconcile_control_total.json

## Dokumentasi Context7 yang Dibaca
- Python/cpython: `pathlib.Path.exists` dan pembacaan CSV ringan.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada checkpoint BE-00.

## File Dibuat/Diubah
- portal_backend/services/lakehouse.py
- portal_backend/app.py

## Implementasi
Endpoint dibuat:
```text
GET /api/lakehouse/summary
```

Aturan ready:
- Bronze ready jika ingestion metadata tersedia.
- Silver ready jika tiga file silver tersedia.
- Gold ready jika dua file gold tersedia.
- Gold valid jika reconcile control total berstatus `pass`.

## Command yang Dijalankan
```bash
Invoke-RestMethod -Uri http://localhost:8091/api/lakehouse/summary
```

## Hasil Validasi
Endpoint tidak error saat folder/file belum ada dan dapat membaca status layer setelah pipeline berjalan.

## Masalah / Risiko
Jumlah file Bronze bersifat indikatif karena backend hanya perlu memastikan metadata utama tersedia.

## Keputusan Teknis
Ringkasan memakai status `ready`/`waiting` agar mudah dipakai UI.

## Langkah Berikutnya
Membuat upload dan preview API.

## Status
Selesai
