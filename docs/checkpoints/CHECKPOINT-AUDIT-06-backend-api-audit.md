# CHECKPOINT-AUDIT-06: Backend API Audit

Tanggal: 2026-05-28
Status: Selesai

## Command

```powershell
.\scripts\start_portal_backend.ps1
Invoke-WebRequest -Uri "http://localhost:8091/api/health" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8091/api/status/services" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8091/api/pdf/sample-status" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8091/api/metrics" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8091/api/lakehouse/summary" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8091/api/activity" -UseBasicParsing
```

## GET Endpoint

```text
GET /api/health -> 200
GET /api/status/services -> 200
GET /api/pdf/sample-status -> 200
GET /api/metrics -> 200
GET /api/activity -> 200
GET /api/lakehouse/summary -> 200
GET /api/data/preview?layer=gold&limit=3 -> 200
GET /api/data/rejected-rows?limit=3 -> 200
```

Payload keys:

```text
/api/health: ['basis', 'mode', 'service', 'status']
/api/status/services: ['services']
/api/pdf/sample-status: ['available', 'method', 'ocr_required', 'path', 'raw_path', 'raw_pdf_available']
/api/metrics: ['available', 'control_total', 'control_total_proposal', 'data_freshness', 'data_freshness_raw', 'data_quality_score', 'pipeline_latency', 'pipeline_latency_raw', 'quality_gate', 'raw']
/api/activity: ['activities', 'message']
/api/lakehouse/summary: ['bronze', 'gold', 'silver']
/api/data/preview: ['available', 'columns', 'limit', 'path', 'rows']
/api/data/rejected-rows: ['available', 'columns', 'limit', 'path', 'rows']
```

## POST Pipeline Endpoint

```text
POST /api/pipeline/generate-data -> 200 status=success
POST /api/pipeline/quality-gate -> 200 status=success
POST /api/pipeline/bronze -> 200 status=success
POST /api/pipeline/silver -> 200 status=success
POST /api/pipeline/gold -> 200 status=success
POST /api/pipeline/metrics -> 200 status=success
POST /api/pipeline/validate-gold -> 200 status=success
POST /api/pipeline/full-run-basic -> 200 status=success mode=local-basic
```

## Empty / Invalid State Safety

Invalid layer:

```text
GET /api/data/preview?layer=bad&limit=3 -> 404
{"available":false,"columns":[],"limit":3,"message":"Layer atau file tidak valid.","rows":[]}
```

Path traversal attempt:

```text
GET /api/data/preview?layer=gold&file=../../README.md -> 404
{"available":false,"columns":[],"limit":10,"message":"File tidak ditemukan: data/generated/gold/README.md","rows":[]}
```

Path traversal tidak keluar dari direktori layer karena filename diproses dengan `secure_filename` dan hasil resolve diverifikasi tetap di bawah base directory.

## Subprocess Safety

File yang diaudit:

```text
portal_backend/services/pipeline.py
```

Hasil:

- `subprocess.run` memakai list args, bukan string command.
- Tidak ada `shell=True`.
- Command pipeline diambil dari mapping statis `COMMANDS`, bukan input bebas user.
- `cwd` dikunci ke `ROOT_DIR`.
- Ada timeout.
- stdout/stderr dipotong dengan `_tail`.

## Upload Safety

File yang diaudit:

```text
portal_backend/services/files.py
```

Hasil:

- Upload memakai `werkzeug.utils.secure_filename`.
- Ekstensi dibatasi per tipe: PDF `.pdf`, CSV `.csv`, Excel `.xlsx`.
- Target path di-resolve dan dicek tetap berada dalam target upload directory.
- `MAX_CONTENT_LENGTH` Flask diset 25 MB.

## Acceptance

- Backend hidup: PASS.
- Semua GET endpoint aman: PASS.
- Empty/invalid state tidak crash: PASS.
- Pipeline endpoint memakai subprocess aman: PASS.
- Tidak memakai `shell=True` untuk input user: PASS.
- Tidak ada path traversal upload/preview yang berhasil keluar directory: PASS.
- Laporan dibuat: PASS.
