# CHECKPOINT-BE-03: Metrics API

## Tujuan
Membaca metrics JSON dan ringkasan quality gate dari output pipeline lokal.

## File Dibaca
- outputs/metrics/reconcile_control_total.json
- outputs/metrics/pipeline_latency.json
- outputs/metrics/data_freshness.json
- outputs/metrics/dropout_rate.json
- outputs/metrics/data_quality_score.json
- data/quarantine/logs/quality_gate_summary.json

## Dokumentasi Context7 yang Dibaca
- Python/cpython: `json` dan `pathlib` untuk pembacaan file aman.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada checkpoint BE-00.

## File Dibuat/Diubah
- portal_backend/services/metrics.py
- portal_backend/app.py

## Implementasi
Endpoint dibuat:
```text
GET /api/metrics
```

Jika file tersedia, backend mengembalikan metrik aktual. Jika file belum tersedia, backend mengembalikan empty state.

## Command yang Dijalankan
```bash
Invoke-RestMethod -Uri http://localhost:8091/api/metrics
```

## Hasil Validasi
Endpoint berhasil mengembalikan:
- Total piutang: `31250000`
- Jumlah penunggak: `15`
- Data Quality Score: `100.0`
- Status validasi: `pass`

## Masalah / Risiko
Beberapa file metrics mungkin belum ada sebelum pipeline dijalankan; UI harus tetap menampilkan empty state.

## Keputusan Teknis
Nilai kontrol tetap mengikuti output pipeline jika tersedia, dengan fallback dummy aman untuk UI.

## Langkah Berikutnya
Membuat API ringkasan Lakehouse.

## Status
Selesai
