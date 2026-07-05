const API_BASE_URL = (() => {
  let params = new URLSearchParams(window.location.search);
  let configured = window.SILARAS_API_BASE_URL || localStorage.getItem("SILARAS_API_BASE_URL") || params.get("api_base");
  if (configured) return configured.replace(/\/$/, "");
  if (window.location.port === "8090") return "http://127.0.0.1:8091";
  return window.location.origin;
})();

const DEFAULT_PRODI = "Sains Data";
const DATA_FONT = "Inter, Plus Jakarta Sans, sans-serif";
const FILTERS = [
  ["tahun_anggaran", "Tahun Anggaran", "calendar_month"],
  ["semester", "Periode", "list_alt"],
  ["nama_prodi", "Prodi", "school"],
  ["kualitas", "Kualitas", "fact_check"],
  ["iku", "IKU", "analytics"],
  ["kegiatan", "Kegiatan", "event_note"],
  ["akun", "Akun", "account_balance"],
];
const filterLabels = Object.fromEntries(FILTERS.map(([key, label]) => [key, label]));
const chartPalette = ["#0f4c81", "#9ca3af", "#ef4444", "#0b63b6", "#22c55e", "#f59e0b"];

let state = {
  payload: null,
  filters: {},
  charts: {},
  chartPayloads: {},
  tableSearch: "",
  tableLimit: 10,
  tableOffset: 0,
  activeTableTab: "detail",
  showAllClusters: false,
};

let globalChartFallbackBound = false;

function rupiah(value) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 })
    .format(Number(value || 0))
    .replace(/\s/g, "");
}

function plainRupiah(value) {
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 }).format(Number(value || 0));
}

function compactRupiah(value) {
  let numberValue = Number(value || 0);
  if (Math.abs(numberValue) >= 1000000000) return `${Math.round(numberValue / 100000000) / 10}M`;
  if (Math.abs(numberValue) >= 1000000) return `${Math.round(numberValue / 1000000)}jt`;
  if (Math.abs(numberValue) >= 1000) return `${Math.round(numberValue / 1000)}rb`;
  return String(Math.round(numberValue));
}

function number(value) {
  return new Intl.NumberFormat("id-ID").format(Number(value || 0));
}

function escapeHtml(value) {
  return String(value ?? "-")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function apiGet(path) {
  let response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  let payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message || `GET ${path} gagal (${response.status})`);
  return payload;
}

function filterQuery() {
  let params = new URLSearchParams();
  for (let [key, value] of Object.entries(state.filters)) {
    if (value) params.set(key, value);
  }
  return params.toString();
}

function dashboardQuery() {
  let params = new URLSearchParams(filterQuery());
  params.set("limit", String(state.tableLimit));
  params.set("offset", String(state.tableOffset));
  return params.toString();
}

async function loadDashboard() {
  let refreshButton = document.getElementById("refreshDashboard");
  refreshButton?.classList.add("loading");
  state.payload = await apiGet(`/api/local-dashboard/all?${dashboardQuery()}`).catch((error) => ({
    status: "failed",
    source: null,
    message: error.message,
    data: null,
  }));

  let availableProdi = state.payload?.data?.filters?.nama_prodi || [];
  if (!state.filters.nama_prodi && availableProdi.includes(DEFAULT_PRODI)) {
    state.filters.nama_prodi = DEFAULT_PRODI;
    state.payload = await apiGet(`/api/local-dashboard/all?${dashboardQuery()}`).catch(() => state.payload);
  }
  render();
  refreshButton?.classList.remove("loading");
}

function renderSource(payload) {
  let sourceStatus = document.getElementById("sourceStatus");
  let sourceInline = document.getElementById("sourceInline");
  let footerStatus = document.getElementById("footerStatus");
  let footerStorage = document.getElementById("footerStorage");
  let isReady = payload.status === "validated" || payload.status === "empty_after_filter";
  sourceStatus.classList.toggle("error", !isReady);
  sourceStatus.textContent = payload.source
    ? `${payload.status}: ${payload.source_dataset || payload.source_kind || "Gold"}`
    : payload.status || "not_available";
  footerStatus.textContent = isReady ? "Operasional" : "Perlu data";
  footerStorage.textContent = payload.source_dataset || "Gold belum tersedia";

  let rowCount = payload.data?.summary?.row_count ?? payload.data?.status?.filtered_row_count;
  sourceInline.innerHTML = `<span class="dot"></span>
    <span>Status: <strong>${escapeHtml(payload.status || "not_available")}</strong></span>
    <span>Baris: <strong>${rowCount !== undefined ? number(rowCount) : "-"}</strong></span>
    <span>Dataset: <strong>${escapeHtml(payload.source_dataset || "-")}</strong></span>
    <span>Sumber: <strong>${escapeHtml(payload.source || "-")}</strong></span>`;
}

function renderFilters(filters) {
  let filterGrid = document.getElementById("filterGrid");
  filterGrid.innerHTML = FILTERS.map(([key, label, icon]) => {
    let values = filters[key] || [];
    let selected = String(state.filters[key] || "");
    return `<label class="filter-field">
      <span class="material-symbols-outlined" aria-hidden="true">${icon}</span>
      <select data-filter="${key}" aria-label="${label}">
        <option value="">${key === "tahun_anggaran" ? "Tahun" : label}: Semua</option>
        ${values.map((value) => `<option value="${escapeHtml(value)}" ${selected === String(value) ? "selected" : ""}>${escapeHtml(value)}</option>`).join("")}
      </select>
    </label>`;
  }).join("");

  for (let select of document.querySelectorAll("[data-filter]")) {
    select.addEventListener("change", () => {
      let key = select.getAttribute("data-filter");
      if (select.value) state.filters[key] = select.value;
      else delete state.filters[key];
      state.tableOffset = 0;
      state.showAllClusters = false;
      loadDashboard();
    });
  }
}

function renderActiveFilters() {
  let active = document.getElementById("activeFilters");
  let entries = Object.entries(state.filters).filter(([, value]) => value);
  active.innerHTML = entries.length
    ? entries.map(([key, value]) => `<span class="chip">${escapeHtml(filterLabels[key] || key)}: ${escapeHtml(value)}</span>`).join("")
    : `<span class="chip">Semua data aktif</span>`;
}

function renderStatusPanel(payload) {
  let panel = document.getElementById("statusPanel");
  if (payload.status === "validated" || payload.status === "empty_after_filter") {
    panel.innerHTML = "";
    panel.className = "status-panel";
    return;
  }
  panel.className = "status-panel";
  panel.innerHTML = `<div class="empty-state">
    <strong>${escapeHtml(payload.message || "Gold dashboard view belum tersedia.")}</strong>
    <p>Dashboard tidak menampilkan angka sampai Gold tersedia. Untuk deploy Vercel, arahkan <code>SILARAS_API_BASE_URL</code> atau query <code>?api_base=...</code> ke backend API.</p>
  </div>`;
}

function renderKpis(summary) {
  let labels = state.payload?.data?.labels || {};
  let cards = [
    {
      label: labels.value_label || "Total Anggaran",
      value: summary ? rupiah(summary.total_nominal_piutang_rp) : "-",
      note: labels.value_note || "dari Gold",
      icon: "payments",
      featured: true,
    },
    {
      label: labels.entity_label || "Item Unik",
      value: summary ? `${number(summary.total_debitur_unik)} Item` : "-",
      note: labels.entity_note || "berdasarkan item unik",
      icon: "description",
    },
    {
      label: "Jumlah IKU",
      value: summary ? `${number(summary.total_iku_unik || 0)} IKU` : "-",
      note: "terhubung dengan alokasi",
      icon: "ads_click",
    },
    {
      label: "Jumlah Kegiatan",
      value: summary ? `${number(summary.total_kegiatan_unik || 0)} Kegiatan` : "-",
      note: "alokasi kegiatan aktif",
      icon: "event_available",
    },
  ];
  document.getElementById("kpiGrid").innerHTML = cards.map((item) => `<article class="kpi-card${item.featured ? " featured" : ""}">
    <span class="material-symbols-outlined kpi-icon" aria-hidden="true">${item.icon}</span>
    <div class="kpi-label">${escapeHtml(item.label)}</div>
    <div class="kpi-value">${escapeHtml(item.value)}</div>
    <div class="kpi-note">${escapeHtml(item.note)}</div>
  </article>`).join("");
}

function findChartIdFromElement(element) {
  let idByElement = {
    chartTahunAnggaran: "bar_by_tahun_anggaran",
    chartKualitas: "donut_by_kualitas",
    chartTahunAkademik: "line_by_tahun_akademik",
    chartSemester: "bar_by_semester",
    chartProdi: "bar_by_prodi",
  };
  return idByElement[element.id] || null;
}

function applyChartFallbackFilter(element, event) {
  let id = findChartIdFromElement(element);
  let chartPayload = id ? state.chartPayloads[id] : null;
  let column = chartPayload?.filter_column;
  let items = chartItemsForDisplay(id, chartPayload);
  if (!column || !items.length) return;
  let rect = element.getBoundingClientRect();
  let ratio = Math.max(0, Math.min(0.999, (event.clientX - rect.left) / Math.max(rect.width, 1)));
  let index = Math.min(items.length - 1, Math.floor(ratio * items.length));
  let label = items[index]?.label;
      if (!label || state.filters[column] === label) return;
  state.filters[column] = label;
  state.tableOffset = 0;
  state.showAllClusters = false;
  loadDashboard();
}

function bindGlobalChartFallback() {
  if (globalChartFallbackBound) return;
  document.addEventListener("pointerdown", (event) => {
    let path = event.composedPath ? event.composedPath() : [];
    let chartElement = path.find((node) => node?.dataset?.testid?.startsWith("local-chart-"));
    if (!chartElement && event.target?.closest) chartElement = event.target.closest("[data-testid^='local-chart-']");
    if (chartElement) applyChartFallbackFilter(chartElement, event);
  }, true);
  globalChartFallbackBound = true;
}

function chartItemsForDisplay(id, payload) {
  let items = payload?.items || [];
  if (id === "bar_by_tahun_anggaran") {
    return [...items].sort((a, b) => String(a.label).localeCompare(String(b.label), "id", { numeric: true }));
  }
  return items;
}

function chartOption(id, payload) {
  let items = chartItemsForDisplay(id, payload);
  if (id === "donut_by_kualitas") {
    let total = items.reduce((sum, item) => sum + Number(item.jumlah_mhs_penunggak || 0), 0);
    return {
      color: chartPalette,
      textStyle: { fontFamily: DATA_FONT },
      tooltip: { trigger: "item", formatter: "{b}: {c} baris ({d}%)" },
      series: [{
        type: "pie",
        radius: ["58%", "78%"],
        center: ["50%", "50%"],
        avoidLabelOverlap: true,
        label: { show: false },
        data: items.map((item) => ({ name: qualityLabel(item.label), value: Number(item.jumlah_mhs_penunggak || 0) })),
      }],
      graphic: [{
        type: "text",
        left: "center",
        top: "42%",
        style: { text: compactRows(total), fill: "#1a1c1d", font: `800 28px ${DATA_FONT}`, textAlign: "center" },
      }, {
        type: "text",
        left: "center",
        top: "55%",
        style: { text: "BARIS", fill: "rgba(65,71,83,.65)", font: `700 12px ${DATA_FONT}`, letterSpacing: 2, textAlign: "center" },
      }],
    };
  }

  return {
    color: ["#0f4c81"],
    textStyle: { fontFamily: DATA_FONT },
    grid: { left: 48, right: 24, top: 24, bottom: 44 },
    tooltip: { trigger: "axis", valueFormatter: (value) => rupiah(value) },
    xAxis: {
      type: "category",
      data: items.map((item) => item.label),
      axisLabel: { color: "rgba(65,71,83,.62)", fontFamily: DATA_FONT, fontWeight: 600 },
      axisLine: { lineStyle: { color: "rgba(193,198,213,.38)" } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "rgba(26,28,29,.06)" } },
      axisLabel: { color: "rgba(65,71,83,.58)", fontFamily: DATA_FONT, fontWeight: 500, formatter: (value) => compactRupiah(value) },
    },
    series: [{
      type: "bar",
      data: items.map((item) => Number(item.nominal_piutang_rp || 0)),
      barMaxWidth: 120,
      itemStyle: { borderRadius: [8, 8, 0, 0], color: "#0f4c81" },
      label: {
        show: true,
        position: "top",
        color: "#0f4c81",
        fontFamily: DATA_FONT,
        fontWeight: 700,
        formatter: (params) => compactRupiah(params.value),
      },
    }],
  };
}

function compactRows(value) {
  let count = Number(value || 0);
  if (count >= 1000) return `${Math.round(count / 100) / 10}k`;
  return number(count);
}

function renderCharts(charts) {
  if (!window.echarts || !charts) return;
  bindGlobalChartFallback();
  state.chartPayloads = charts;
  for (let [id, elementId] of Object.entries({
    bar_by_tahun_anggaran: "chartTahunAnggaran",
    donut_by_kualitas: "chartKualitas",
  })) {
    let element = document.getElementById(elementId);
    let chartPayload = charts[id];
    if (!element || !chartPayload) continue;
    if (state.charts[id]) state.charts[id].dispose();
    let chart = window.echarts.init(element);
    chart.setOption(chartOption(id, chartPayload));
    chart.on("click", (params) => {
      let column = chartPayload.filter_column;
      if (!column || !params.name) return;
      state.filters[column] = params.name;
      state.tableOffset = 0;
      state.showAllClusters = false;
      loadDashboard();
    });
    state.charts[id] = chart;
  }
}

function renderQualityLegend(items) {
  let total = items.reduce((sum, item) => sum + Number(item.jumlah_mhs_penunggak || 0), 0) || 1;
  document.getElementById("qualityLegend").innerHTML = items.slice(0, 5).map((item, index) => {
    let pct = Math.round((Number(item.jumlah_mhs_penunggak || 0) / total) * 100);
    return `<div class="legend-item">
      <span class="legend-label"><span class="legend-swatch" style="background:${chartPalette[index % chartPalette.length]}"></span>${escapeHtml(qualityLabel(item.label))}</span>
      <strong>${pct}%</strong>
    </div>`;
  }).join("");
}

function renderTrendNarrative(items) {
  if (!items?.length) {
    document.getElementById("trendNarrative").textContent = "Tidak ada data anggaran pada filter aktif.";
    return;
  }
  let top = [...items].sort((a, b) => Number(b.nominal_piutang_rp || 0) - Number(a.nominal_piutang_rp || 0))[0];
  document.getElementById("trendNarrative").textContent = `Tahun ${top.label} menjadi periode dengan alokasi terbesar (~Rp${compactRupiah(top.nominal_piutang_rp)})`;
}

function renderYearSummary(items) {
  let target = document.getElementById("yearSummaryList");
  if (!target) return;
  let rows = [...(items || [])].sort((a, b) => String(b.label).localeCompare(String(a.label), "id", { numeric: true }));
  if (!rows.length) {
    target.innerHTML = `<div class="kpi-note">Tidak ada ringkasan tahun pada filter aktif.</div>`;
    return;
  }
  target.innerHTML = `<div class="year-summary-header">
    <span>Tahun</span>
    <span>Anggaran</span>
    <span>Items</span>
  </div>
  ${rows.map((item) => `<div class="year-summary-row">
    <span>${escapeHtml(item.label)}</span>
    <span>Rp${escapeHtml(compactRupiah(item.nominal_piutang_rp))}</span>
    <span>${number(item.debitur_unik || item.jumlah_mhs_penunggak || 0)}</span>
  </div>`).join("")}`;
}

function renderRankList(targetId, items, options = {}) {
  let target = document.getElementById(targetId);
  if (!target) return;
  let rows = (items || []).slice(0, options.limit || 4);
  let total = (items || []).reduce((sum, item) => sum + Number(item.nominal_piutang_rp || 0), 0);
  let max = Math.max(...rows.map((item) => Number(item.nominal_piutang_rp || 0)), 1);
  target.innerHTML = rows.length
    ? rows.map((item, index) => {
      let amount = Number(item.nominal_piutang_rp || 0);
      let pct = options.percentTotal
        ? Math.round((amount / Math.max(total, 1)) * 100)
        : Math.round((amount / max) * 100);
      let barPct = Math.max(4, pct);
      let value = options.percent
        ? `${pct}%`
        : `${compactRupiah(amount)}`;
      return `<div class="rank-row${index === rows.length - 1 ? " muted" : options.subtle ? " subtle" : ""}">
        <div class="rank-row-header"><span>${escapeHtml(item.label)}</span><span>${escapeHtml(value)}</span></div>
        <div class="track"><div class="bar" style="width:${barPct}%"></div></div>
      </div>`;
    }).join("")
    : `<div class="kpi-note">Tidak ada data pada filter aktif.</div>`;
}

function renderClusterTreemap(items) {
  let target = document.getElementById("clusterTreemap");
  if (!target) return;
  let allRows = items || [];
  let rows = state.showAllClusters ? allRows.slice(0, 12) : allRows.slice(0, 4);
  if (!rows.length) {
    target.innerHTML = `<div class="empty-state"><strong>Tidak ada cluster kegiatan.</strong><p>Ubah filter untuk melihat distribusi kegiatan per IKU.</p></div>`;
    return;
  }
  target.classList.toggle("expanded", state.showAllClusters);
  let otherRows = allRows.slice(4);
  let otherTotal = Math.max(0, otherRows.reduce((sum, item) => sum + Number(item.nominal_piutang_rp || 0), 0));
  target.innerHTML = rows.map((item, index) => {
    let { code, title } = splitClusterLabel(item.label);
    return `<button type="button" class="treemap-tile size-${index + 1}" data-treemap-filter="${escapeHtml(item.label)}">
      <span>
        <span class="treemap-code" title="${escapeHtml(code)}">${escapeHtml(compactClusterCode(code))}</span>
        <span class="treemap-title">${escapeHtml(title)}</span>
      </span>
      <span class="treemap-value">${compactRupiah(item.nominal_piutang_rp)}</span>
    </button>`;
  }).join("") + (state.showAllClusters
    ? `<button type="button" class="treemap-tile other compact" data-collapse-clusters="true">
      <strong>Tampilkan ringkas</strong>
      <span class="treemap-other-note">Kembali ke 4 kegiatan utama</span>
    </button>`
    : `<button type="button" class="treemap-tile other" data-expand-clusters="true" ${otherTotal ? "" : "disabled"}>
      <strong>Lainnya (${compactRupiah(otherTotal)})</strong>
      <span class="treemap-other-note">${number(otherRows.length)} kegiatan lain</span>
    </button>`);

  for (let button of target.querySelectorAll("[data-treemap-filter]")) {
    button.addEventListener("click", () => {
      let value = button.getAttribute("data-treemap-filter");
      if (!value) return;
      state.filters.kegiatan = value;
      state.tableOffset = 0;
      state.showAllClusters = false;
      loadDashboard();
    });
  }
  target.querySelector("[data-expand-clusters]")?.addEventListener("click", () => {
    state.showAllClusters = true;
    renderClusterTreemap(items);
  });
  target.querySelector("[data-collapse-clusters]")?.addEventListener("click", () => {
    state.showAllClusters = false;
    renderClusterTreemap(items);
  });
}

function splitClusterLabel(value) {
  let label = String(value || "-");
  let parts = label.split(" - ");
  if (parts.length < 2) return { code: "Kegiatan", title: label };
  return { code: parts[0], title: parts.slice(1).join(" - ") };
}

function compactClusterCode(value) {
  let code = String(value || "Kegiatan");
  if (code === "Kegiatan") return code;
  let short = code.split(".").slice(0, 3).join(".");
  return short ? `Kode ${short}` : "Kode kegiatan";
}

function qualityClass(value) {
  let text = String(value || "").toLowerCase();
  if (text.includes("ok") || text.includes("lancar") || text.includes("valid")) return "ok";
  if (text.includes("review") || text.includes("pending") || text.includes("rule") || text.includes("diragukan")) return "warn";
  if (text.includes("macet") || text.includes("bad") || text.includes("fail")) return "bad";
  return "";
}

function qualityLabel(value) {
  let text = String(value || "-").trim();
  let normalized = text.toUpperCase();
  if (normalized === "VALIDATED_WITH_RULE") return "VALID_RULE";
  if (normalized === "REVIEW_QUEUE") return "REVIEW";
  if (normalized === "MAPPED_BY_CODE") return "MAPPED";
  if (normalized === "MAPPED_FROM_SOURCE") return "MAPPED";
  return text.replaceAll("_", " ");
}

function filteredRows(rows) {
  let term = state.tableSearch.trim().toLowerCase();
  if (!term) return rows;
  return rows.filter((row) => Object.values(row).some((value) => String(value ?? "").toLowerCase().includes(term)));
}

function syncTableTabs() {
  for (let button of document.querySelectorAll("[data-tab]")) {
    button.classList.toggle("active", button.getAttribute("data-tab") === state.activeTableTab);
  }
}

function renderValidationRecap() {
  let target = document.getElementById("detailTable");
  let items = state.payload?.data?.charts?.donut_by_kualitas?.items || [];
  let total = items.reduce((sum, item) => sum + Number(item.jumlah_mhs_penunggak || 0), 0);
  if (!items.length) {
    target.innerHTML = `<div class="empty-state"><strong>Tidak ada rekap validasi.</strong><p>Ubah filter untuk melihat distribusi kualitas mapping.</p></div>`;
    return;
  }
  target.innerHTML = `<div class="table-wrap validation-wrap">
    <table data-testid="local-validation-table">
      <thead><tr>
        <th>Quality</th><th style="text-align:right;">Baris</th><th style="text-align:right;">Persentase</th><th>Status Data</th><th>Sumber</th>
      </tr></thead>
      <tbody>${items.map((item) => {
        let rows = Number(item.jumlah_mhs_penunggak || 0);
        let pct = total ? Math.round((rows / total) * 100) : 0;
        let label = qualityLabel(item.label);
        let status = label === "OK" ? "Tervalidasi" : label.includes("REVIEW") ? "Perlu review" : "Validasi berbasis rule";
        return `<tr>
          <td><span class="quality-pill ${qualityClass(item.label)}">${escapeHtml(label)}</span></td>
          <td class="amount-cell">${number(rows)}</td>
          <td class="amount-cell">${pct}%</td>
          <td class="strong-cell">${escapeHtml(status)}</td>
          <td class="truncate-cell">${escapeHtml(state.payload?.source || "-")}</td>
        </tr>`;
      }).join("")}</tbody>
    </table>
  </div>
  <div class="table-footer">
    <span>Rekap berdasarkan <strong>${number(total)}</strong> baris pada filter aktif</span>
    <span>${escapeHtml(state.payload?.source_dataset || "Gold lokal")}</span>
  </div>`;
}

function renderTable(table) {
  let target = document.getElementById("detailTable");
  let labels = state.payload?.data?.labels || {};
  syncTableTabs();
  if (state.activeTableTab === "validasi") {
    renderValidationRecap();
    return;
  }
  let rows = filteredRows(table?.rows || []);
  if (!rows.length) {
    target.innerHTML = `<div class="empty-state"><strong>Tidak ada baris detail.</strong><p>Ubah filter atau kata pencarian untuk melihat item biaya.</p></div>`;
    return;
  }
  let totalRows = Number(table?.total_rows || 0);
  let offset = Number(table?.offset || state.tableOffset || 0);
  let limit = Number(table?.limit || state.tableLimit || rows.length || 1);
  let pageStart = totalRows && rows.length ? offset + 1 : 0;
  let pageEnd = Math.min(offset + rows.length, totalRows);
  let currentPage = Math.floor(offset / Math.max(limit, 1)) + 1;
  let hasPrevious = offset > 0;
  let hasNext = offset + limit < totalRows;
  target.innerHTML = `<div class="table-wrap">
    <table data-testid="local-detail-table">
      <thead><tr>
        <th>Thn</th><th>Periode</th><th>IKU</th><th>Kegiatan</th><th>Akun</th><th>Uraian Detail</th><th style="text-align:right;">Jumlah (Rp)</th><th>Quality</th>
      </tr></thead>
      <tbody>${rows.map((row) => {
        let kegiatan = row.kegiatan && row.kegiatan !== "-" ? row.kegiatan : row.nama_debitur;
        let uraian = row.uraian_detail && row.uraian_detail !== "-" ? row.uraian_detail : row.nama_debitur;
        let mapping = row.mapping_status || row.kualitas || "-";
        let quality = row.kualitas || "-";
        return `<tr title="Mapping: ${escapeHtml(mapping)}">
          <td>${escapeHtml(row.tahun_anggaran || row.tahun_akademik)}</td>
          <td>${escapeHtml(row.semester)}</td>
          <td class="primary-cell">${escapeHtml(row.iku || "-")}</td>
          <td class="strong-cell">${escapeHtml(kegiatan)}</td>
          <td>${escapeHtml(row.akun || "-")}</td>
          <td class="truncate-cell">${escapeHtml(uraian)}</td>
          <td class="amount-cell">${plainRupiah(row.nominal_piutang_rp)}</td>
          <td><span class="quality-pill ${qualityClass(quality)}">${escapeHtml(qualityLabel(quality))}</span></td>
        </tr>`;
      }).join("")}</tbody>
    </table>
  </div>
  <div class="table-footer">
    <span>Menampilkan <strong>${number(pageStart)} - ${number(pageEnd)}</strong> dari ${number(totalRows)} baris data</span>
    <div class="pagination" aria-label="Navigasi halaman tabel">
      <button type="button" class="pager-button" data-page-action="prev" ${hasPrevious ? "" : "disabled"} aria-label="Halaman sebelumnya">
        <span class="material-symbols-outlined" aria-hidden="true">chevron_left</span>
      </button>
      <button type="button" class="pager-button active" aria-current="page">${number(currentPage)}</button>
      <button type="button" class="pager-button" data-page-action="next" ${hasNext ? "" : "disabled"} aria-label="Halaman berikutnya">
        <span class="material-symbols-outlined" aria-hidden="true">chevron_right</span>
      </button>
    </div>
  </div>`;

  for (let button of target.querySelectorAll("[data-page-action]")) {
    button.addEventListener("click", () => {
      let action = button.getAttribute("data-page-action");
      state.tableOffset = action === "next" ? offset + limit : Math.max(0, offset - limit);
      loadDashboard();
    });
  }
}

function updateTitles(data) {
  let labels = data.labels || {};
  if (labels.title) document.querySelector("h1").textContent = labels.title;
  if (labels.subtitle) {
    let subtitle = labels.subtitle;
    if (state.payload?.source_dataset === "fact_anggaran") {
      subtitle = "Ruang kendali anggaran berbasis Gold fact_anggaran. Data selaras dengan Superset SILARAS.";
    }
    document.getElementById("dashboardSubtitle").innerHTML = escapeHtml(subtitle)
      .replace("Gold fact_anggaran", "<strong>Gold fact_anggaran</strong>")
      .replace("vw_dashboard_piutang_ukt", "<strong>vw_dashboard_piutang_ukt</strong>");
  }
  let prodi = state.filters.nama_prodi || DEFAULT_PRODI;
  document.getElementById("prodiPill").innerHTML = `<span class="material-symbols-outlined" aria-hidden="true">school</span><span>Prodi: ${escapeHtml(prodi)}</span>`;
  document.getElementById("tableHeading").textContent = state.activeTableTab === "validasi" ? "Validasi Rekap" : "Data Item Biaya";
  document.getElementById("tableSubtitle").textContent = state.activeTableTab === "validasi"
    ? `Ringkasan kualitas mapping untuk Prodi ${prodi} pada filter aktif.`
    : `Menampilkan item anggaran detail untuk Prodi ${prodi}.`;
}

function render() {
  let payload = state.payload || { status: "not_available", data: null };
  let data = payload.data || {};
  updateTitles(data);
  renderSource(payload);
  renderFilters(data.filters || {});
  renderActiveFilters();
  renderStatusPanel(payload);

  let available = payload.status === "validated" || payload.status === "empty_after_filter";
  document.getElementById("kpiGrid").style.display = available ? "grid" : "none";
  document.getElementById("dashboardGrid").style.display = available ? "grid" : "none";
  if (!available) return;

  renderKpis(data.summary);
  renderTrendNarrative(data.charts?.bar_by_tahun_anggaran?.items || []);
  renderYearSummary(data.charts?.bar_by_tahun_anggaran?.items || []);
  renderQualityLegend(data.charts?.donut_by_kualitas?.items || []);
  renderClusterTreemap(data.charts?.bar_by_kegiatan?.items || []);
  renderRankList("ikuRankList", data.charts?.bar_by_iku?.items || data.charts?.bar_by_prodi?.items || [], { limit: 5 });
  renderRankList("accountBudgetList", data.charts?.bar_by_akun?.items || [], { limit: 4, subtle: true });
  renderRankList("kegiatanRankList", data.charts?.bar_by_kegiatan?.items || [], { subtle: true });
  renderRankList("akunRankList", data.charts?.bar_by_akun?.items || [], { percent: true, percentTotal: true, subtle: true });
  renderTable(data.table);
  window.setTimeout(() => renderCharts(data.charts), 0);
}

function downloadTableCsv() {
  let table = state.payload?.data?.table;
  let rows = filteredRows(table?.rows || []);
  if (!rows.length) return;
  let headers = ["tahun", "periode", "iku", "kegiatan", "akun", "uraian_detail", "jumlah", "mapping", "quality"];
  let csvRows = [headers.join(",")];
  for (let row of rows) {
    let values = [
      row.tahun_anggaran || row.tahun_akademik,
      row.semester,
      row.iku || "-",
      row.kegiatan || row.nama_debitur,
      row.akun || "-",
      row.uraian_detail || row.nama_debitur,
      row.nominal_piutang_rp,
      row.mapping_status || row.kualitas,
      row.kualitas,
    ].map((value) => `"${String(value ?? "").replace(/"/g, '""')}"`);
    csvRows.push(values.join(","));
  }
  let blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8" });
  let url = URL.createObjectURL(blob);
  let link = document.createElement("a");
  link.href = url;
  link.download = "silaras-dashboard-detail.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

document.getElementById("resetFilters").addEventListener("click", () => {
  state.filters = {};
  state.tableOffset = 0;
  state.showAllClusters = false;
  loadDashboard();
});

document.getElementById("refreshDashboard").addEventListener("click", () => {
  loadDashboard();
});

document.getElementById("downloadCsv").addEventListener("click", downloadTableCsv);

document.getElementById("tableSearch").addEventListener("input", (event) => {
  state.tableSearch = event.target.value;
  renderTable(state.payload?.data?.table);
});

document.getElementById("tablePageSize").addEventListener("change", (event) => {
  state.tableLimit = Number(event.target.value || 10);
  state.tableOffset = 0;
  loadDashboard();
});

for (let button of document.querySelectorAll("[data-tab]")) {
  button.addEventListener("click", () => {
    state.activeTableTab = button.getAttribute("data-tab") || "detail";
    state.tableOffset = 0;
    updateTitles(state.payload?.data || {});
    renderTable(state.payload?.data?.table);
  });
}

window.addEventListener("resize", () => {
  for (let chart of Object.values(state.charts)) chart.resize();
});

loadDashboard();
