from __future__ import annotations

import re
from pathlib import Path


V2_INDEX = Path(__file__).resolve().parents[1] / "portal" / "v2" / "index.html"


def _html() -> str:
    return V2_INDEX.read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    html = _html()
    start = html.find(f"async function {name}(")
    assert start != -1
    open_idx = html.index("{", start)
    depth = 0
    end = None
    for i in range(open_idx, len(html)):
        ch = html[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    assert end is not None
    return html[open_idx + 1 : end]


def test_v2_resolves_backend_api_base_for_local_frontend_ports_and_proxy_origin() -> None:
    html = _html()

    assert "function resolveApiBaseUrl()" in html
    assert 'params.get("api_base")' in html
    assert "window.SILARAS_API_BASE_URL" in html
    assert "const port = window.location.port;" in html
    assert 'port === "8090"' in html
    assert "`${proto}//${host}:8091`" in html
    assert 'port === "8190"' in html
    assert "`${proto}//${host}:8191`" in html
    assert "return window.location.origin;" in html
    assert "const API_BASE_URL = resolveApiBaseUrl();" in html


def test_v2_loads_all_authoritative_dashboard_status_endpoints() -> None:
    html = _html()

    for endpoint in [
        "/api/superset/summary",
        "/api/metrics",
        "/api/airflow/active",
        "/api/airflow/latest",
        "/api/system-truth/status",
        "/api/excel-lakehouse/status",
    ]:
        assert (
            f'apiGetCached("{endpoint}", 8000)' in html
            or f'apiGetCached("{endpoint}",' in html
            or f'apiGet("{endpoint}")' in html
            or f'apiGet("{endpoint}",' in html
        )

    assert "Promise.allSettled" in html
    assert "buildPortalViewModel({" in html


def test_v2_api_fetches_include_credentials_for_cross_origin_cookie_auth() -> None:
    html = _html()

    assert 'credentials: "include"' in html
    assert 'headers: { "Content-Type": "application/json" }' in html
    assert "if (!res.ok) throw new Error" in html


def test_v2_maps_live_fact_quality_and_pipeline_fields_into_view_model() -> None:
    html = _html()

    assert "function buildPortalViewModel" in html
    assert "Object.freeze({" in html
    assert "supersetSummary.total_jumlah" in html
    assert "supersetSummary.total_weighted_iku" in html
    assert "supersetSummary.fact_rows" in html
    assert "metrics.data_quality_score" in html
    assert "excelLakehouse.fact_anggaran.total_jumlah" in html
    assert "excelLakehouse.counts?.fact_anggaran_rows" in html
    assert 'document.getElementById("valTotalAnggaran")' in html
    assert 'id="valTotalWeightedIku"' in html
    assert re.search(r'setText\(\s*"valTotalWeightedIku"', html)
    assert 'document.getElementById("valItemAnggaran")' in html
    assert 'document.getElementById("valQualityScore")' in html
    assert 'document.getElementById("valPipelineStatus")' in html


def test_v2_pipeline_status_distinguishes_success_running_failed_missing_unreachable() -> None:
    html = _html()

    assert "const STATUS_VIEW = Object.freeze({" in html
    for state in ["success", "running", "failed", "missing", "unreachable"]:
        assert f'"{state}"' in html
    assert "function normalizeStatusKind" in html
    assert "function authoritativePipelineState" in html


def test_v2_medallion_runtime_is_airflow_authoritative() -> None:
    html = _html()

    assert "function renderLiveStepper" in html
    assert "function currentAirflowProgress" in html
    assert "runData?.progress?.stages" in html
    assert "STAGE_KEYS" in html
    assert "function stageTimingHtml" in html
    assert "stage.duration_seconds" in html
    assert "function formatStageDuration" in html
    assert "function tickLiveStepper" in html
    assert "setInterval(tickLiveStepper, 1000)" in html
    assert "renderLiveStepper._lastHtml" in html
    assert "apiGetCached(" in html
    assert "`/api/airflow/runs/${encodeURIComponent(runId)}`" in html
    assert "medallion-pipeline-flow" in html
    assert "stage-timing running" in html
    assert "stage-timing done" in html
    assert "stage-timing idle" in html
    assert "menunggu" in html
    assert "progressHtml" not in html


def test_v2_pipeline_trigger_polls_run_detail_and_reports_error() -> None:
    html = _html()
    body = _function_body("triggerAirflowAndWait")

    assert 'apiPost("/api/airflow/trigger", {})' in html
    assert "`/api/airflow/runs/${encodeURIComponent(runId)}`" in html
    assert "setTimeout(resolve, 1500)" in body
    assert "setButtonsRunning(true)" in body
    assert "setButtonsRunning(false)" in body
    assert "Gagal menjalankan Airflow" in body
    assert "function apiErrorMessage" in html
    assert "payload.message" in html


def test_v2_stepper_uses_live_step_states_instead_of_static_all_ready() -> None:
    html = _html()

    assert "function liveWorkflowSteps" in html
    assert "function renderLiveStepper" in html
    assert "const progress =" in html
    assert ".map((step, idx)" in html
    assert "const isStageRunning" in html
    assert "effectiveState" in html
    assert "ready: true" not in html


def test_v2_shows_meaningful_loading_and_unreachable_error_states() -> None:
    html = _html()

    assert "function renderLoadingState()" in html
    assert "function renderErrorState(error)" in html
    assert "Memuat data live dari backend SILARAS" in html
    assert "API backend belum dapat dijangkau" in html
    assert "state.portalLoadStatus = \"loading\"" in html
    assert "state.portalLoadStatus = \"unreachable\"" in html


def test_v2_upload_rejects_non_ok_http_responses_before_success_ui() -> None:
    body = _function_body("handleUploadSubmit")

    assert "if (!res.ok)" in body
    assert "Upload Gagal" in body
    assert "Workbook Excel berhasil diunggah!" in body
    assert body.index("if (!res.ok)") < body.index("Workbook Excel berhasil diunggah!")


def test_v2_upload_modes_preserve_file_details_and_append_session() -> None:
    html = _html()
    upload_body = _function_body("handleUploadSubmit")

    assert 'name="upload_mode"' in html
    assert 'name="append_to_active"' in html
    assert "function setUploadMetadataState" in html
    assert "function refreshSelectedUploadDetails" in html
    assert "pendingUploadFiles" in html
    assert "function removePendingUploadFile" in html
    assert 'category === "multi"' in html
    assert "setUploadMetadataState(category)" in html
    assert "input.disabled" in html
    assert "File ${i + 1} dari ${files.length}" not in html
    for label in ["Tahun:", "Periode:", "Prodi:", "Fakultas:"]:
        assert label in html
    assert "append_to_active" in upload_body
    assert 'formData.append("file_excel[]"' in upload_body
    assert 'formData.set("file_metadata"' in upload_body
    assert "refreshUploadSession" in upload_body
    assert "function inferUploadKind" in html
    assert "inferUploadKind(file.name, metadata.jenis_dataset)" in html


def test_v2_has_no_fullscreen_loading_overlay_or_runtime_controller() -> None:
    html = _html()

    for marker in [
        "loading-overlay",
        "appLoadingOverlay",
        "pipelineLoadingOverlay",
        "showPipelineLoading",
        "hidePipelineLoading",
    ]:
        assert marker not in html


def test_v2_safe_escapes_html_before_uat_rows_use_inner_html() -> None:
    html = _html()

    assert "function escapeHtml(value)" in html
    for escaped in ["&amp;", "&lt;", "&gt;", "&quot;", "&#39;"]:
        assert escaped in html
    assert "const safe = (val) =>" in html
    assert "val === undefined || val === null || val === \"\" ? \"-\" : escapeHtml(val);" in html
    for field in [
        "item.time || \"-\"",
        "item.evaluator || \"Evaluator\"",
        "item.module || \"General\"",
        "item.feedback || \"-\"",
    ]:
        assert f"safe({field})" in html


def test_v2_preserves_partial_endpoint_rejections_as_unreachable_statuses() -> None:
    html = _html()

    assert "function settledEndpoint" in html
    assert "endpointStatus" in html
    assert "result.status === \"rejected\"" in html
    assert "status: \"unreachable\"" in html
    assert "endpointStatus.airflowLatest?.status === \"unreachable\"" in html
    assert "partial_error" in html


def test_v2_deep_freezes_view_model_and_nested_steps() -> None:
    html = _html()

    assert "function deepFreeze(value)" in html
    assert "Object.getOwnPropertyNames(value)" in html
    assert "return deepFreeze({" in html
    assert "...viewModel," in html
    assert "steps: liveWorkflowSteps(viewModel)," in html


def test_v2_initial_dom_uses_loading_labels_not_ready_or_online() -> None:
    html = _html()

    assert '<div class="metric-value" id="valPipelineStatus">Menunggu</div>' in html
    assert '<div class="metric-value" id="valPipelineStatus">Ready</div>' not in html
    assert 'id="footerStatusBadge"' not in html
    assert 'id="footerPipelineMsg"' not in html
    assert "SYSTEM LOADING" not in html


def test_v2_dashboard_summary_never_uses_stale_numeric_fallbacks() -> None:
    html = _html()

    for element_id in ["dashTotalAnggaran", "dashFactRows", "dashAkunCount"]:
        assert re.search(
            rf'<div class="metric-value" id="{element_id}">\s*-\s*</div>',
            html,
        )

    assert "Rp 517.361.656" not in html
    assert 'id="dashFactRows">253</div>' not in html
    assert 'id="dashAkunCount">5</div>' not in html
    assert 'summary.total_anggaran !== undefined &&\n            summary.total_anggaran !== null' in html
    assert 'summary.total_rows !== undefined && summary.total_rows !== null' in html
    assert 'summary.total_akun !== undefined && summary.total_akun !== null' in html
    assert 'id="dashSummaryStatus"' in html
    assert "Data ringkasan Superset belum tersedia." in html
    assert "summaryStatus.style.display" in html


def test_v2_task3_has_navigation_and_views_for_all_primary_workflows() -> None:
    html = _html()

    for page in ["beranda", "orkestrasi", "review-iku", "lakehouse", "dashboard", "analytics", "system"]:
        assert f'data-page="{page}"' in html
        assert f'id="view-{page}"' in html

    for title in [
        "Orkestrasi",
        "Verifikasi IKU",
        "Riwayat Data",
        "Dashboard BI",
        "Evaluasi UAT",
        "Status Server",
    ]:
        assert title in html

    assert "Halaman sedang disiapkan" not in html
    assert "missing-page-placeholder" not in html.lower()


def test_v2_task3_wires_existing_backend_endpoints_without_frontend_business_logic() -> None:
    html = _html()

    for endpoint in [
        "/api/upload/session/status",
        "/api/airflow/active",
        "/api/airflow/latest",
        "/api/airflow/runs",
        "/api/iku-review/queue?limit=100",
        "/api/storage/manifest",
        "/api/data/preview?layer=gold&limit=10",
        "/api/data/preview?layer=silver&limit=10",
        "/api/dashboard/links/current",
        "/api/uat/summary",
        "/api/system-truth/status",
        "/api/metrics",
        "/api/status/services",
    ]:
        assert (
            f'apiGetCached("{endpoint}", 8000)' in html
            or f'apiGetCached("{endpoint}",' in html
            or f'apiGet("{endpoint}")' in html
            or f'apiGet("{endpoint}",' in html
        )

    assert 'apiPost("/api/airflow/trigger", {})' in html
    assert "`/api/airflow/runs/${encodeURIComponent(runId)}`" in html
    assert 'apiPost("/api/iku-review/override", payload)' in html
    assert 'apiPost("/api/uat/submit", {' in html
    assert 'mode: "local_feedback",' in html
    assert "...entry," in html


def test_v2_task3_review_iku_instruction_and_accessible_save_flow() -> None:
    html = _html()

    assert "function renderIkuReviewQueue" in html
    assert "function handleIkuOverrideSave" in html
    assert "Review IKU tersimpan. Buka Eksekusi -> Jalankan Sistem." in html
    assert "Eksekusi -> Jalankan Sistem" in html
    assert 'class="input-apple iku-search-input"' in html
    assert 'class="btn-apple btn-secondary iku-review-save"' in html
    assert "data-item-id" in html


def test_v2_task3_dynamic_tables_escape_backend_and_user_content() -> None:
    html = _html()

    for renderer in [
        "renderUploadSession",
        "renderAirflowPanel",
        "renderIkuReviewQueue",
        "renderStorageManifest",
        "renderDataPreviews",
        "renderDashboardLinks",
        "renderUatOfficialSummary",
        "renderSystemStatus",
    ]:
        assert f"function {renderer}" in html

    unsafe_patterns = [
        "${row.item_id}",
        "${row.kegiatan}",
        "${row.feedback}",
        "${file.filename}",
        "${link.url}",
        "${service.status}",
    ]
    for pattern in unsafe_patterns:
        assert pattern not in html

    for safe_pattern in [
        "${safe(row.item_id)}",
        "${safe(row.kegiatan)}",
        "${safe(file.filename)}",
        "${safeUrl(link.url)}",
        "statusBadgeHtml(service.status, service.status)",
    ]:
        assert safe_pattern in html

    assert "function normalizedSystemServices" in html
    assert "Array.isArray(source)" in html
    assert "service.name || service.key || service.id" in html


def test_v2_task3_uat_official_matrix_and_local_submissions_are_separate() -> None:
    html = _html()

    assert 'id="uatOfficialMatrix"' in html
    assert 'id="tblUatSubmissions"' in html
    assert "Riwayat Evaluasi Pengguna" in html
    assert "Matriks UAT Resmi" in html
    assert "renderUatOfficialSummary" in html
    assert "state.uatSummary" in html


def test_v2_exposes_delete_controls_for_committed_uploads() -> None:
    html = _html()

    assert "async function deleteActiveUploadFile" in html
    assert "async function deleteAllActiveUploads" in html
    assert 'apiDelete("/api/upload/session/file"' in html
    assert 'apiDelete("/api/upload/session"' in html
    assert "Hapus file tersimpan" in html
    assert "Hapus semua file tersimpan" in html
    assert "confirm(" in html
