# CHECKPOINT-BE-MAIN-05: Metrics API

## Tujuan
Membuat response metrics lebih eksplisit mengikuti `main.pdf`.

## File Dibaca
- outputs/metrics/reconcile_control_total.json
- outputs/metrics/pipeline_latency.json
- outputs/metrics/data_freshness.json
- outputs/metrics/dropout_rate.json
- outputs/metrics/data_quality_score.json
- portal_backend/services/metrics.py

## Dokumentasi Context7 yang Dibaca
- Python/cpython: json dan pathlib.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- portal_backend/services/metrics.py
- portal_backend/services/pipeline.py

## Implementasi
Endpoint:
```text
GET  /api/metrics
POST /api/pipeline/metrics
POST /api/pipeline/validate-gold
```

Response metrics menambahkan `control_total_proposal`:
- expected_total_piutang
- actual_total_piutang
- expected_penunggak
- actual_penunggak
- status

## Command yang Dijalankan
```bash
python src/metrics/reconcile_control_total.py
python src/metrics/pipeline_latency.py
python src/metrics/data_freshness.py
python src/metrics/dropout_rate.py
python src/metrics/data_quality_score.py
Invoke-RestMethod -Uri http://localhost:8091/api/metrics
```

## Hasil Validasi
Metrics terbaca:
- Data Quality Score: 100.0
- Dropout Rate: 2.0
- expected/actual total piutang: 31250000
- expected/actual penunggak: 15
- status: pass

## Masalah / Risiko
Jika metrics belum pernah dijalankan, endpoint tetap mengembalikan empty state.

## Keputusan Teknis
Field lama dipertahankan agar UI sebelumnya tetap kompatibel.

## Langkah Berikutnya
Memastikan activity lineage.

## Status
Selesai
