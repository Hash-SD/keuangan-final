from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V2_INDEX = ROOT / "portal" / "v2" / "index.html"


def _v2_script() -> str:
    html = V2_INDEX.read_text(encoding="utf-8")
    scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", html, flags=re.I)
    assert len(scripts) == 1
    return scripts[0]


def test_v2_script_runtime_adapter_smoke(tmp_path: Path) -> None:
    harness = f"""
const vm = require("vm");
const assert = require("assert");

const nodes = {{}};
function makeNode(id) {{
  return {{
    id,
    value: "",
    files: [],
    dataset: {{}},
    disabled: false,
    textContent: "",
    innerHTML: "",
    className: "",
    style: {{}},
    setAttribute() {{}},
    getAttribute() {{ return null; }},
    classList: {{ add() {{}}, remove() {{}}, toggle() {{}} }},
    querySelector() {{ return null; }},
    querySelectorAll() {{ return []; }},
    appendChild() {{}},
    insertBefore() {{}},
    removeChild() {{}},
    firstChild: null,
    scrollTop: 0,
    children: {{ length: 0 }}
  }};
}}

const context = {{
  assert,
  console,
  Error,
  Intl,
  URL,
  URLSearchParams,
  setTimeout() {{ return 0; }},
  clearTimeout() {{}},
  FormData: class FormData {{
    constructor(form) {{ this.form = form; }}
  }},
  localStorage: {{
    store: {{}},
    getItem(key) {{ return Object.prototype.hasOwnProperty.call(this.store, key) ? this.store[key] : null; }},
    setItem(key, value) {{ this.store[key] = String(value); }},
    removeItem(key) {{ delete this.store[key]; }}
  }},
  window: {{
    location: {{ search: "", port: "8090", protocol: "http:", hostname: "localhost", origin: "http://localhost:8090" }},
    SILARAS_API_BASE_URL: undefined,
    addEventListener() {{}}
  }},
  document: {{
    getElementById(id) {{
      if (!nodes[id]) nodes[id] = makeNode(id);
      return nodes[id];
    }},
    addEventListener() {{}},
    createElement() {{ return makeNode(""); }},
    querySelector() {{ return null; }},
    querySelectorAll() {{ return []; }}
  }},
  fetch: async () => ({{ ok: true, status: 200, json: async () => ({{}}) }})
}};
context.window.localStorage = context.localStorage;
context.window.document = context.document;
context.globalThis = context;

const script = {json.dumps(_v2_script())};
const testCode = `
"use strict";
(async () => {{
  const viewModel = buildPortalViewModel({{
    supersetSummary: {{
      status: "ready",
      total_jumlah: 125000,
      total_weighted_iku: 50000,
      fact_rows: 42
    }},
    metrics: {{ data_quality_score: 97 }},
    airflowLatest: {{
      status: "success",
      run: {{
        state: "success",
        dag_run_id: "dag-success",
        end_date: "2026-08-01T01:02:03Z"
      }}
    }},
    systemTruth: {{
      generated_at: "2026-08-01T01:03:00Z",
      layers: {{
        raw: {{ status: "ready" }},
        bronze: {{ status: "ready" }},
        silver: {{ status: "ready" }},
        gold: {{ status: "ready" }}
      }},
      dashboard: {{ status: "created" }},
      services: {{ superset: {{ status: "ready", url: "http://localhost:8089" }} }}
    }},
    excelLakehouse: {{
      fact_anggaran: {{ total_jumlah: 1, total_weighted_iku: 2 }},
      counts: {{ fact_anggaran_rows: 3 }},
      artifacts: {{}},
      metadata: {{ pipeline_run_id: "fallback-run" }}
    }}
  }});

  assert.strictEqual(viewModel.total_jumlah, 125000);
  assert.strictEqual(viewModel.total_weighted_iku, 50000);
  assert.strictEqual(viewModel.fact_rows, 42);
  assert.strictEqual(viewModel.data_quality_score, 97);
  assert.strictEqual(viewModel.pipeline.statusKind, "success");
  assert.strictEqual(viewModel.steps.at(-1).statusKind, "success");
  assert.ok(Object.isFrozen(viewModel));
  assert.ok(Object.isFrozen(viewModel.steps));
  assert.ok(Object.isFrozen(viewModel.steps[0]));
  assert.ok(Object.isFrozen(viewModel.supersetSummary));
  assert.throws(() => {{ viewModel.steps[0].statusKind = "failed"; }}, TypeError);

  const endpointStatus = {{
    supersetSummary: settledEndpoint("supersetSummary", {{ status: "fulfilled", value: {{ status: "ready", total_jumlah: 9, total_weighted_iku: 8, fact_rows: 7 }} }}),
    metrics: settledEndpoint("metrics", {{ status: "fulfilled", value: {{ data_quality_score: 88 }} }}),
    airflowLatest: settledEndpoint("airflowLatest", {{ status: "rejected", reason: new Error("airflow down") }}),
    systemTruth: settledEndpoint("systemTruth", {{ status: "fulfilled", value: {{ layers: {{}} }} }}),
    excelLakehouse: settledEndpoint("excelLakehouse", {{ status: "fulfilled", value: {{ fact_anggaran: {{}}, counts: {{}}, artifacts: {{}} }} }})
  }};
  const partial = buildPortalViewModel({{
    supersetSummary: endpointStatus.supersetSummary.value,
    metrics: endpointStatus.metrics.value,
    airflowLatest: endpointStatus.airflowLatest.value,
    systemTruth: endpointStatus.systemTruth.value,
    excelLakehouse: endpointStatus.excelLakehouse.value,
    endpointStatus
  }});
  assert.strictEqual(partial.endpointStatus.airflowLatest.status, "unreachable");
  assert.strictEqual(partial.pipeline.statusKind, "unreachable");
  assert.strictEqual(partial.loadStatus, "partial_error");

  assert.strictEqual(escapeHtml("<b&\\\\"'>"), "&lt;b&amp;&quot;&#39;&gt;");
  assert.strictEqual(safe("<img src=x onerror=alert(1)>"), "&lt;img src=x onerror=alert(1)&gt;");
  assert.strictEqual(safe(""), "-");
  assert.strictEqual(safeUrl("javascript:alert(1)"), "#");
  assert.strictEqual(safeUrl("data:text/html,evil"), "#");
  assert.strictEqual(safeUrl("vbscript:msgbox(1)"), "#");
  assert.strictEqual(safeUrl("https://evil.example/dashboard"), "#");
  assert.strictEqual(safeUrl("http://localhost:8089/superset/dashboard/1"), "http://localhost:8089/superset/dashboard/1");
  assert.strictEqual(safeUrl("/local-dashboard/"), "/local-dashboard/");

  const apiCalls = [];
  fetch = async (url, options = {{}}) => {{
    apiCalls.push({{ url: String(url), options }});
    return {{ ok: true, status: 200, json: async () => ({{ ok: true }}) }};
  }};
  await apiGet("/api/credential-get");
  await apiPost("/api/credential-post", {{ hello: "world" }});
  assert.strictEqual(apiCalls[0].options.credentials, "include");
  assert.strictEqual(apiCalls[1].options.credentials, "include");
  assert.strictEqual(apiCalls[1].options.method, "POST");
  assert.strictEqual(apiCalls[1].options.headers["Content-Type"], "application/json");
  assert.strictEqual(apiCalls[1].options.body, JSON.stringify({{ hello: "world" }}));

  const uploadCalls = [];
  fetch = async (url, options = {{}}) => {{
    uploadCalls.push({{ url: String(url), options }});
    return {{ ok: false, status: 500, json: async () => ({{ status: "failed" }}) }};
  }};
  document.getElementById("excelUploadForm");
  document.getElementById("btnUploadSubmit");
  document.getElementById("uploadStatusBadge");
  document.getElementById("appToast");
  document.getElementById("toastText");
  await handleUploadSubmit({{ preventDefault() {{}} }});
  assert.strictEqual(uploadCalls[0].options.credentials, "include");
  assert.strictEqual(uploadCalls[0].options.method, "POST");
  assert.strictEqual(document.getElementById("uploadStatusBadge").textContent, "Upload Gagal");
  assert.notStrictEqual(document.getElementById("uploadStatusBadge").textContent, "Upload Sukses");
  assert.match(document.getElementById("toastText").textContent, /Gagal mengunggah/);

  const trickyItemId = 'item-"[data-x="boom]';
  const encodedOverride = encodeURIComponent(JSON.stringify({{ iku_codes: "IKU-1", detail_id: "detail-1" }}));
  const trickySelect = {{ value: encodedOverride, dataset: {{ itemId: trickyItemId }} }};
  const requestedUrls = [];
  fetch = async (url, options = {{}}) => {{
    requestedUrls.push(String(url).replace("http://localhost:8091", ""));
    if (String(url).includes("/api/iku-review/override")) {{
      const body = JSON.parse(options.body);
      assert.strictEqual(body.item_id, trickyItemId);
      return {{ ok: true, status: 200, json: async () => ({{ status: "saved" }}) }};
    }}
    if (String(url).includes("/api/iku-review/queue")) {{
      return {{ ok: true, status: 200, json: async () => ({{ rows: [], iku_options: [] }}) }};
    }}
    return {{ ok: true, status: 200, json: async () => ({{}}) }};
  }};
  document.querySelectorAll = (selector) => selector === ".iku-review-select" ? [trickySelect] : [];
  document.querySelector = () => {{ throw new Error("raw querySelector must not be used for Review IKU item lookup"); }};
  await handleIkuOverrideSave({{ dataset: {{ itemId: trickyItemId }} }});
  assert.ok(requestedUrls.includes("/api/iku-review/override"));

  const payloadByPath = {{
    "/api/upload/session/status": {{ status: "committed", dataset_session_id: "dataset-1", files: [{{ filename: "<rab>.xlsx", jenis_dataset: "rab" }}], message: "ready" }},
    "/api/airflow/active": {{ status: "running", active: true, dag_run_id: "dag-1", dataset_session_id: "dataset-1" }},
    "/api/airflow/latest": {{ status: "success", run: {{ state: "success", dag_run_id: "dag-old" }} }},
    "/api/iku-review/queue?limit=100": {{ rows: [{{ item_id: "item-1", kegiatan: "<script>", uraian_detail: "detail", jumlah: 10, kode_iku: "IKU", nama_iku: "Nama" }}], iku_options: [{{ iku_raw: "IKU", detail_id: "d1", detail_kegiatan: "Kegiatan" }}] }},
    "/api/storage/manifest": {{ layers: {{ gold: {{ status: "ready", local_path: "data/gold", s3_prefix: "s3://bucket/gold" }} }} }},
    "/api/data/preview?layer=gold&limit=10": {{ data: [{{ item_id: "gold-1", kegiatan: "<gold>" }}] }},
    "/api/data/preview?layer=silver&limit=10": {{ data: [{{ item_id: "silver-1", kegiatan: "<silver>" }}] }},
    "/api/dashboard/links/current": {{ dashboard_url: "javascript:alert(1)", dashboard_urls_by_year: {{ "Lokal": "http://localhost:8089/superset/dashboard/1", "Evil": "https://evil.example/x" }} }},
    "/api/uat/summary": {{ status: "completed", matrix: [{{ name: "Clarity", score: 5, status: "completed" }}] }},
    "/api/system-truth/status": {{ services: {{ superset: {{ status: "ready", url: "http://localhost:8089" }} }} }},
    "/api/metrics": {{ data_quality_score: 91 }},
    "/api/status/services": {{ services: [
      {{ key: "superset", name: "Apache Superset", role: "BI", status: "ready", url: "http://localhost:8089" }},
      {{ key: "airflow", name: "Apache Airflow", role: "Orchestrator", status: "running", url: "http://localhost:8085" }}
    ] }}
  }};
  const featureUrls = [];
  fetch = async (url) => {{
    const path = String(url).replace("http://localhost:8091", "");
    featureUrls.push(path);
    const payload = payloadByPath[path];
    return {{ ok: Boolean(payload), status: payload ? 200 : 404, json: async () => payload || {{ status: "missing" }} }};
  }};
  document.querySelectorAll = () => [];
  await fetchFeatureParityData();
  for (const path of Object.keys(payloadByPath)) assert.ok(featureUrls.includes(path), path);
  assert.match(document.getElementById("uploadSessionPanel").innerHTML, /&lt;rab&gt;\\.xlsx/);
  assert.match(document.getElementById("tblIkuReviewRows").innerHTML, /&lt;script&gt;/);
  assert.ok(document.getElementById("dashboardLinksPanel").innerHTML.includes('href="#"'));
  assert.ok(document.getElementById("dashboardLinksPanel").innerHTML.includes("http://localhost:8092/"));
  assert.ok(!document.getElementById("dashboardLinksPanel").innerHTML.includes("https://evil.example"));
  const listServiceHtml = document.getElementById("tblServicesStatus").innerHTML;
  assert.ok(listServiceHtml.includes("Apache Superset"));
  assert.ok(listServiceHtml.includes("Apache Airflow"));
  assert.ok(!listServiceHtml.includes("<strong>0</strong>"));

  renderSystemStatus({{ services: {{ trino: {{ name: "Trino Coordinator", role: "SQL Engine", status: "ready", url: "http://localhost:8080" }} }} }});
  const objectServiceHtml = document.getElementById("tblServicesStatus").innerHTML;
  assert.ok(objectServiceHtml.includes("Trino Coordinator"));
  assert.ok(objectServiceHtml.includes("SQL Engine"));
}})()
`;

(async () => {{
  vm.createContext(context);
  vm.runInContext(script, context, {{ filename: "portal-v2-script.js" }});
  await vm.runInContext(testCode, context, {{ filename: "portal-v2-runtime-smoke.js" }});
  console.log("portal v2 runtime smoke ok");
}})().catch(error => {{
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
}});
"""
    harness_path = tmp_path / "portal_v2_runtime_smoke.js"
    harness_path.write_text(harness, encoding="utf-8")

    result = subprocess.run(
        ["node", str(harness_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "portal v2 runtime smoke ok" in result.stdout
