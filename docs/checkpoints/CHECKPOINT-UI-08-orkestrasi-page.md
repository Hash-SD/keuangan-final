# CHECKPOINT-UI-08: Orkestrasi Page

## Tujuan
Membuat halaman Orkestrasi untuk Airflow/DAG, execution flow, task instance, dan logs.

## File Dibaca
- `portal/index.html`
- `dags/keuangan_prodi_lakehouse_dag.py`
- `outputs/metrics/pipeline_latency.json`
- `stitch_uc_data_portal_design/orkestrasi_portal_keuangan_sidebar/code.html`

## Dokumentasi Context7 yang Dibaca
- Docker Compose: port mapping Airflow host 8085 ke container 8080.
- MDN Web Docs: responsive overflow untuk pipeline flow.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada UI-00.

## File Dibuat/Diubah
- `portal/index.html`
- `docs/checkpoints/CHECKPOINT-UI-08-orkestrasi-page.md`

## Implementasi
Orkestrasi memuat:
- DAG Name `keuangan_prodi_lakehouse_dag`.
- DAG Status.
- Last Run.
- Execution Time.
- Next Run.
- Trigger DAG Button disabled dengan label menunggu integrasi API.
- Open Airflow Button ke `http://localhost:8085`.
- Pipeline Execution Flow.
- Task Instance Detail.
- Logs Panel.

## Command yang Dijalankan
```bash
Select-String -Path portal/index.html -Pattern "keuangan_prodi_lakehouse_dag|localhost:8085"
```

## Hasil Validasi
- Flow tampil dan bisa horizontal scroll.
- Link Airflow benar.
- Trigger DAG tidak menjalankan aksi palsu dari browser.

## Masalah / Risiko
- Belum ada endpoint POST trigger DAG.

## Keputusan Teknis
- Semua aksi DAG yang berdampak dibuat disabled sampai backend/API tersedia.

## Langkah Berikutnya
Lanjut `CHECKPOINT-UI-09-analytics-page.md`.

## Status
Selesai
