# CHECKPOINT-UI-07: Lakehouse Page

## Tujuan
Membuat halaman Lakehouse untuk Bronze, Silver, Gold, lineage, dan validasi Gold.

## File Dibaca
- `portal/index.html`
- `portal/server.py`
- `data/generated/bronze/ingestion_metadata.json`
- `data/generated/silver/fact_piutang_ukt_prodi.csv`
- `data/generated/silver/transactions_clean.csv`
- `data/generated/silver/rab_prodi_sains_data_long.csv`
- `data/generated/gold/fact_piutang_ukt_prodi.csv`
- `data/generated/gold/vw_dashboard_piutang_ukt.csv`
- `outputs/metrics/reconcile_control_total.json`
- `stitch_uc_data_portal_design/lakehouse_layers_medallion_observability_v2/code.html`

## Dokumentasi Context7 yang Dibaca
- MDN Web Docs: responsive layout dan semantic sections.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada UI-00.

## File Dibuat/Diubah
- `portal/index.html`
- `portal/server.py`
- `docs/checkpoints/CHECKPOINT-UI-07-lakehouse-page.md`

## Implementasi
Lakehouse memuat:
- Bronze Layer Card.
- Silver Layer Card.
- Gold Layer Card.
- Data Lineage Diagram: PDF Audited, CSV Transaksi, Excel RAB ke Bronze, Silver, Gold, Trino, Superset.
- Layer History.
- Validate Gold Section.

Aturan status:
- Bronze ready jika ingestion metadata tersedia.
- Silver ready jika tiga CSV Silver tersedia.
- Gold ready jika dua CSV Gold tersedia.
- Gold valid jika reconcile status `pass`.

## Command yang Dijalankan
```bash
Invoke-WebRequest -Uri http://localhost:8090/api/portal-state -UseBasicParsing
```

## Hasil Validasi
- Bronze/Silver/Gold jelas.
- Validasi Gold menampilkan expected/actual total piutang dan penunggak.
- Jika validasi belum ada, empty state tampil.

## Masalah / Risiko
- Row count layer tidak dihitung penuh agar portal tetap ringan.

## Keputusan Teknis
- Status layer berbasis keberadaan file, sesuai instruksi.

## Langkah Berikutnya
Lanjut `CHECKPOINT-UI-08-orkestrasi-page.md`.

## Status
Selesai
