# CHECKPOINT-UI-06: Dashboard Page

## Tujuan
Membuat halaman Dashboard untuk monitoring metrik dan status pipeline.

## File Dibaca
- `portal/index.html`
- `outputs/metrics/data_quality_score.json`
- `outputs/metrics/dropout_rate.json`
- `outputs/metrics/pipeline_latency.json`
- `outputs/metrics/data_freshness.json`
- `outputs/metrics/reconcile_control_total.json`
- `outputs/reports/superset_assets.json`
- `outputs/reports/superset_dashboard.json`
- `stitch_uc_data_portal_design/dashboard_portal_keuangan_sidebar/code.html`

## Dokumentasi Context7 yang Dibaca
- MDN Web Docs: Fetch API dan DOM rendering.
- Docker Compose: service port mapping untuk Superset host 8089.

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
- `docs/checkpoints/CHECKPOINT-UI-06-dashboard-page.md`

## Implementasi
Dashboard memuat:
- Data Quality Score.
- Dropout Rate.
- Pipeline Latency.
- Data Freshness.
- Rejected Rows.
- Gold Validation.
- Pipeline Data Flow.
- Superset Section.
- Last Activity.

Superset dashboard diarahkan ke:
`http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/`

## Command yang Dijalankan
```bash
Select-String -Path portal/index.html -Pattern "Dropout Rate|8089|dashboard-piutang-ukt-prodi"
```

## Hasil Validasi
- Istilah `Dropout Rate` konsisten.
- Superset section memuat status, nama dashboard, dataset aktif, last refresh, dan tombol dashboard.
- Tidak ada port Superset 8088 pada UI.

## Masalah / Risiko
- Superset status menjadi `Offline` jika service lokal tidak berjalan.

## Keputusan Teknis
- Status dashboard mendukung `Ready`, `Waiting for Gold`, `Waiting for Metrics`, `Superset Offline`, dan `Validation Failed`.

## Langkah Berikutnya
Lanjut `CHECKPOINT-UI-07-lakehouse-page.md`.

## Status
Selesai
