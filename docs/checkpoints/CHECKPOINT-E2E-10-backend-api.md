# CHECKPOINT-E2E-10 - Backend API

Tanggal: 2026-05-28
Status: PASS

## Perintah

```powershell
.\scripts\start_portal_backend.ps1
```

Hasil:

```text
Portal frontend aktif: http://localhost:8090
Portal backend aktif: http://localhost:8091/api/health
```

## GET Endpoint

Endpoint wajib:

```text
/api/health -> 200
/api/status/services -> 200
/api/pdf/sample-status -> 200
/api/metrics -> 200
/api/lakehouse/summary -> 200
/api/activity -> 200
```

Ringkasan payload:

```text
/api/health keys=['basis', 'mode', 'service', 'status']
/api/status/services keys=['services']
/api/pdf/sample-status keys=['available', 'method', 'ocr_required', 'path', 'raw_path', 'raw_pdf_available']
/api/metrics keys=['available', 'control_total', 'control_total_proposal', 'data_freshness', 'data_freshness_raw', 'data_quality_score', 'pipeline_latency', 'pipeline_latency_raw', 'quality_gate', 'raw']
/api/lakehouse/summary keys=['bronze', 'gold', 'silver']
/api/activity keys=['activities', 'message']
```

## POST Pipeline Endpoint

Endpoint pipeline wajib:

```text
quality-gate  -> 200 status=success metrics_status=pass
bronze        -> 200 status=success
silver        -> 200 status=success
gold          -> 200 status=success
metrics       -> 200 status=success metrics_status=pass
validate-gold -> 200 status=success metrics_status=pass
```

Activity log setelah pengujian:

```text
activity_count=41
```

## Acceptance

- Semua endpoint wajib OK: PASS.
- API mengembalikan structured JSON: PASS.
- Pipeline endpoint punya success response: PASS.
- Activity log tertulis: PASS.
- Metrics endpoint tetap menunjukkan rekonsiliasi PASS: PASS.
- Jika file output ada, API membaca output aktual: PASS.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-11-ui-backend-integration.md`.
