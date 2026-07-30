# Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menyiapkan portal dan pipeline agar fail-closed serta siap menerima satu upload final pengguna tanpa memakai data contoh atau mengganti Gold aktif sebelum validasi lengkap.

**Architecture:** Upload disimpan dan divalidasi sepenuhnya di staging sebelum pointer dataset aktif diganti. Pipeline membangun artefak per `dataset_session_id/pipeline_run_id`, menjalankan quality gate, lalu mempublikasikan pointer secara atomik; PostgreSQL dan dashboard diperlakukan sebagai target publish yang tervalidasi. Endpoint readiness hanya menyatakan siap bila runtime bersih, test lulus, dan seluruh layanan sehat.

**Tech Stack:** Python 3, Flask, pandas/openpyxl, PostgreSQL, MinIO, Superset, Airflow, pytest, Docker Compose.

## Global Constraints

- Production tidak boleh membaca sample, fixture, upload lama, atau fallback path; fixture hanya diizinkan saat `APP_ENV=test` atau `ALLOW_SAMPLE_DATA=true`.
- Identitas `dataset_session_id`, `pipeline_run_id`, dan `airflow_dag_run_id` tidak boleh bercampur dan harus ada dalam manifest serta artefak publish.
- Timestamp pengukuran hanya memakai event aktual; data tidak lengkap berstatus `NOT_AVAILABLE`.
- Jangan menghapus source code, test, konfigurasi Docker, evidence archive, atau workbook pengguna di luar repository.
- Cleanup runtime dilakukan setelah backup dan dicatat dalam laporan JSON.

---

### Task 1: Audit dan kontrak fail-closed

**Files:**
- Modify: `dags/keuangan_prodi_excel_lakehouse_dag.py`
- Modify: `src/common/runtime_paths.py`
- Test: `tests/test_production_source_guard.py`

- [ ] Tulis test yang membuktikan production tanpa dataset aktif gagal sebelum Bronze dan DAG tidak mempunyai `SAMPLE_EXCEL_DIR`.
- [ ] Jalankan test untuk memastikan gagal.
- [ ] Hilangkan fallback sample dan source lama, lalu buat resolver hanya menerima manifest committed yang tervalidasi.
- [ ] Jalankan test sampai lulus.

### Task 2: Upload atomik dan terverifikasi

**Files:**
- Modify: `portal_backend/services/excel_upload.py`
- Create: `portal_backend/services/production_state.py`
- Test: `tests/test_production_upload_atomic.py`

- [ ] Tulis test untuk ekstensi, file kosong/rusak, duplikasi, partial bundle, rollback, status STAGING/VALIDATING/COMMITTED, hash, dan pointer lama tetap utuh.
- [ ] Jalankan test untuk memastikan gagal.
- [ ] Implementasikan staging, validasi workbook, metadata lengkap dan atomic replace pointer.
- [ ] Jalankan test sampai lulus.

### Task 3: Pipeline per-run dan quality gate

**Files:**
- Modify: `src/transformations/excel_lakehouse_pipeline.py`
- Create: `src/validation/production_quality_gate.py`
- Test: `tests/test_production_pipeline_atomic.py`

- [ ] Tulis test untuk direktori output per-run, status lifecycle, mismatch ID, gate blocking, dan rollback Gold aktif.
- [ ] Jalankan test untuk memastikan gagal.
- [ ] Implementasikan manifest lifecycle, output staging per-run, validasi Gold, dan pointer publish atomik.
- [ ] Jalankan test sampai lulus.

### Task 4: Publish PostgreSQL/Superset dan readiness

**Files:**
- Modify: `src/sql/load_gold_to_postgres.py`
- Modify: `portal_backend/services/superset_api.py`
- Modify: `portal_backend/app.py`
- Modify: portal upload UI files discovered by inspection
- Test: `tests/test_production_readiness.py`

- [ ] Tulis test untuk staging/validation PostgreSQL, Superset unavailable, timestamp missing/order, dan JSON readiness.
- [ ] Jalankan test untuk memastikan gagal.
- [ ] Implementasikan timestamp publish, verification dari query nyata, readiness endpoint, dan tombol upload disabled jika belum siap.
- [ ] Jalankan test sampai lulus.

### Task 5: Backup, cleanup, release verification

**Files:**
- Create: `scripts/prepare_production_runtime.py`
- Create: `scripts/production_release_gate.py`
- Create: `outputs/reports/cleanup_report.json`
- Create: `outputs/reports/test_report.json`
- Create: `outputs/reports/service_health_report.json`
- Create: `outputs/reports/production_release_gate.json`
- Create: `outputs/reports/production_release_gate.md`

- [ ] Tulis unit test dry-run cleanup dan release decision fail-closed.
- [ ] Jalankan test untuk memastikan gagal.
- [ ] Backup artefak runtime, bersihkan target aktif yang telah diverifikasi, dan hasilkan laporan.
- [ ] Jalankan compileall, seluruh pytest, Docker smoke, endpoint readiness, lalu hasilkan release gate hanya dari hasil aktual.
