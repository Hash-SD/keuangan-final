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
        "/api/airflow/runtime",
        "/api/system-truth/status",
        "/api/excel-lakehouse/status",
    ]:
        assert (
            f'apiGet("{endpoint}")' in html
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

    assert "function resolveRuntimeRun" in html
    assert "Sumber waktu:" in html
    assert "stageData.duration_seconds" in html
    assert "Date.now() - new Date(ti.start_date)" not in html
    assert "airflowLatest.run || airflowLatest" in html
    assert "statusKind === \"running\"" in html
    assert "statusKind === \"failed\"" in html
    assert "medallion-progress-summary" in html
    assert "pipeline-progress-fill" in html
    assert "node-task-detail" in html
    assert "Menunggu ${stageTotal} task Airflow" in html
    assert 'role="status"' in html
    assert "progressHtml" not in html


def test_v2_pipeline_polling_is_single_request_and_silent_until_error() -> None:
    html = _html()
    body = _function_body("triggerAirflowAndWait")

    assert (
        'apiGet("/api/airflow/runtime")' in html
        or 'apiGet("/api/airflow/runtime",' in html
    )
    assert "function fetchAirflowRuntime" in html
    assert "airflowRuntimeRequest" in html
    assert "setTimeout(resolve, 3000)" in body
    assert "showPipelineLoading" not in body
    assert body.count("showToast") == 1
    assert "Gagal menjalankan Airflow" in body


def test_v2_stepper_uses_live_step_states_instead_of_static_all_ready() -> None:
    html = _html()

    assert "function liveWorkflowSteps" in html
    assert "function renderLiveStepper" in html
    assert "const taskInstances = Array.isArray(progress.task_instances)" in html
    assert ".map((step, idx)" in html
    assert "const statusClass = stageHasFailure" in html
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
        "/api/airflow/runtime",
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
            f'apiGet("{endpoint}")' in html
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
    assert "Review IKU tersimpan. Buka Orkestrasi -> Jalankan Sistem." in html
    assert "Orkestrasi -> Jalankan Sistem" in html
    assert 'class="input-apple iku-review-select"' in html
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
