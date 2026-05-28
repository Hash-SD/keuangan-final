# CHECKPOINT-UI-11: Local Data Integration

## Tujuan
Menghubungkan UI dengan file output lokal secara aman.

## File Dibaca
- `portal/server.py`
- `portal/index.html`
- `data/quarantine/logs/quality_gate_summary.json`
- `data/quarantine/logs/rejected_rows.csv`
- `data/generated/bronze/ingestion_metadata.json`
- `data/generated/silver/fact_piutang_ukt_prodi.csv`
- `data/generated/silver/transactions_clean.csv`
- `data/generated/silver/rab_prodi_sains_data_long.csv`
- `data/generated/gold/fact_piutang_ukt_prodi.csv`
- `data/generated/gold/vw_dashboard_piutang_ukt.csv`
- `outputs/metrics/reconcile_control_total.json`
- `outputs/metrics/pipeline_latency.json`
- `outputs/metrics/data_freshness.json`
- `outputs/metrics/dropout_rate.json`
- `outputs/metrics/data_quality_score.json`
- `outputs/reports/superset_assets.json`
- `outputs/reports/superset_dashboard.json`
- `outputs/uat/uat_score_summary.json`

## Dokumentasi Context7 yang Dibaca
- MDN Web Docs: Fetch API dan safe DOM rendering.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada UI-00.

## File Dibuat/Diubah
- `portal/server.py`
- `portal/index.html`
- `scripts/start_portal.ps1`
- `docs/checkpoints/CHECKPOINT-UI-11-local-data-integration.md`

## Implementasi
- Endpoint read-only `/api/portal-state`.
- JSON dibaca dengan fallback `None` jika file tidak ada.
- CSV preview dibaca via `csv.DictReader`.
- Layer status dihitung dari keberadaan file.
- Dashboard status dihitung dari Gold, metrics, Superset, dan validasi Gold.
- Empty state ditampilkan di UI jika data belum ada.

## Command yang Dijalankan
```bash
python -m py_compile portal/server.py
Invoke-WebRequest -Uri http://localhost:8090/api/portal-state -UseBasicParsing
```

## Hasil Validasi
- API portal-state mengembalikan metrics, files, layers, services, preview CSV, dan rejected rows.
- UI tidak error jika file tidak tersedia.
- Preview CSV dibatasi 6 baris pada implementasi saat ini.

## Masalah / Risiko
- Batas preview 6 baris lebih kecil dari rentang 10-25 yang disarankan, dipilih agar UI tetap ringan dan ringkas.

## Keputusan Teknis
- Server lokal hanya read-only, tidak menjalankan pipeline command dari browser.

## Langkah Berikutnya
Lanjut `CHECKPOINT-UI-12-service-links-status.md`.

## Status
Selesai
