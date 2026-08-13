const API_BASE_URL = (() => {
  const params = new URLSearchParams(window.location.search);
  const configured = window.SILARAS_API_BASE_URL || localStorage.getItem("SILARAS_API_BASE_URL") || params.get("api_base");
  if (configured) return configured.replace(/\/$/, "");
  if (window.location.port === "8090") return "http://127.0.0.1:8091";
  if (window.location.port === "8190") return "http://127.0.0.1:8191";
  return window.location.origin;
})();

const DATA_FONT = "Inter, Plus Jakarta Sans, sans-serif";
const FILTERS = [
  ["tahun", "Tahun", "calendar_month"],
  ["prodi", "Prodi", "school"],
  ["iku", "IKU", "analytics"],
  ["kegiatan", "Kegiatan", "event_note"],
  ["akun", "Akun", "account_balance"],
];
const filterLabels = Object.fromEntries(FILTERS.map(([key, label]) => [key, label]));
const chartPalette = ["#0f4c81", "#9ca3af", "#ef4444", "#0b63b6", "#22c55e", "#f59e0b"];

const state = {
  payload: null,
  filters: {},
  charts: {},
  tableSearch: "",
  tableLimit: 10,
  tableOffset: 0,
  activeTableTab: "detail",
  showAllClusters: false,
};

function rupiah(value) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 })
    .format(Number(value || 0)).replace(/\s/g, "");
}

function plainRupiah(value) {
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 }).format(Number(value || 0));
}

function compactRupiah(value) {
  const amount = Number(value || 0);
  if (Math.abs(amount) >= 1000000000) return `${Math.round(amount / 100000000) / 10}M`;
  if (Math.abs(amount) >= 1000000) return `${Math.round(amount / 1000000)}jt`;
  if (Math.abs(amount) >= 1000) return `${Math.round(amount / 1000)}rb`;
  return String(Math.round(amount));
}

function number(value) {
  return new Intl.NumberFormat("id-ID").format(Number(value || 0));
}

function escapeHtml(value) {
  return String(value ?? "-")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message || `GET ${path} gagal (${response.status})`);
  return payload;
}

function filterQuery() {
  const params = new URLSearchParams();
  Object.entries(state.filters).forEach(([key, value]) => { if (value) params.set(key, value); });
  return params.toString();
}

function dashboardQuery() {
  const params = new URLSearchParams(filterQuery());
  params.set("limit", String(state.tableLimit));
  params.set("offset", String(state.tableOffset));
  return params.toString();
}

let loadSequence = 0;
async function loadDashboard() {
  const sequence = ++loadSequence;
  document.getElementById("refreshDashboard")?.classList.add("loading");
  state.payload = await apiGet(`/api/local-dashboard/all?${dashboardQuery()}`).catch((error) => ({
    status: "failed", source: null, message: error.message, data: null,
  }));
  if (sequence !== loadSequence) return;
  render();
  document.getElementById("refreshDashboard")?.classList.remove("loading");
}

function renderSource(payload) {
  const ready = payload.status === "validated" || payload.status === "empty_after_filter";
  const rowCount = payload.data?.summary?.row_count ?? payload.data?.status?.filtered_row_count;
  const sourceStatus = document.getElementById("sourceStatus");
  sourceStatus.classList.toggle("error", !ready);
  sourceStatus.textContent = payload.source ? `${payload.status}: ${payload.source_dataset || "Gold"}` : payload.status || "not_available";
  document.getElementById("footerStatus").textContent = ready ? "Operasional" : "Perlu data";
  document.getElementById("footerStorage").textContent = payload.source_dataset || "Gold belum tersedia";
  document.getElementById("sourceInline").innerHTML = `<span class="dot"></span>
    <span>Status: <strong>${escapeHtml(payload.status || "not_available")}</strong></span>
    <span>Baris: <strong>${rowCount === undefined ? "-" : number(rowCount)}</strong></span>
    <span>Dataset: <strong>${escapeHtml(payload.source_dataset || "-")}</strong></span>
    <span>Sumber: <strong>${escapeHtml(payload.source || "-")}</strong></span>`;
}

function renderFilters(filters) {
  const target = document.getElementById("filterGrid");
  target.innerHTML = FILTERS.map(([key, label, icon]) => {
    const values = filters[key] || [];
    const selected = String(state.filters[key] || "");
    return `<label class="filter-field">
      <span class="material-symbols-outlined" aria-hidden="true">${icon}</span>
      <select data-filter="${key}" aria-label="${label}">
        <option value="">${label}: Semua</option>
        ${values.map((value) => `<option value="${escapeHtml(value)}" ${selected === String(value) ? "selected" : ""}>${escapeHtml(value)}</option>`).join("")}
      </select>
    </label>`;
  }).join("");
  target.querySelectorAll("[data-filter]").forEach((select) => select.addEventListener("change", () => {
    const key = select.getAttribute("data-filter");
    if (select.value) state.filters[key] = select.value;
    else delete state.filters[key];
    state.tableOffset = 0;
    state.showAllClusters = false;
    loadDashboard();
  }));
}

function renderActiveFilters() {
  const entries = Object.entries(state.filters).filter(([, value]) => value);
  document.getElementById("activeFilters").innerHTML = entries.length
    ? entries.map(([key, value]) => `<span class="chip">${escapeHtml(filterLabels[key] || key)}: ${escapeHtml(value)}</span>`).join("")
    : `<span class="chip">Semua data aktif</span>`;
}

function renderStatusPanel(payload) {
  const panel = document.getElementById("statusPanel");
  const ready = payload.status === "validated" || payload.status === "empty_after_filter";
  panel.className = "status-panel";
  panel.innerHTML = ready ? "" : `<div class="empty-state">
    <strong>${escapeHtml(payload.message || "Gold fact_anggaran belum tersedia.")}</strong>
    <p>Dashboard menunggu Gold tahunan yang memenuhi kontrak.</p>
  </div>`;
}

function renderKpis(summary) {
  const labels = state.payload?.data?.labels || {};
  const cards = [
    { label: labels.value_label || "Total Anggaran", value: summary ? rupiah(summary.total_anggaran) : "-", note: "SUM(jumlah_weighted_iku)", icon: "payments", featured: true },
    { label: labels.item_label || "Jumlah Item", value: summary ? `${number(summary.jumlah_item)} Item` : "-", note: "distinct item anggaran", icon: "description" },
    { label: labels.iku_label || "Jumlah IKU", value: summary ? `${number(summary.jumlah_iku)} IKU` : "-", note: "distinct kode IKU", icon: "ads_click" },
    { label: labels.activity_label || "Jumlah Kegiatan", value: summary ? `${number(summary.jumlah_kegiatan)} Kegiatan` : "-", note: "distinct kegiatan", icon: "event_available" },
    { label: labels.status_label || "Status Rekonsiliasi", value: summary?.status_rekonsiliasi || "-", note: "status validasi tahunan", icon: "fact_check" },
  ];
  document.getElementById("kpiGrid").innerHTML = cards.map((item) => `<article class="kpi-card${item.featured ? " featured" : ""}">
    <span class="material-symbols-outlined kpi-icon" aria-hidden="true">${item.icon}</span>
    <div class="kpi-label">${escapeHtml(item.label)}</div>
    <div class="kpi-value">${escapeHtml(item.value)}</div>
    <div class="kpi-note">${escapeHtml(item.note)}</div>
  </article>`).join("");
}

function chartItems(payload) {
  return (payload?.items || []).slice().sort((left, right) => Number(right.total_anggaran || 0) - Number(left.total_anggaran || 0));
}

function chartOption(payload, type = "bar") {
  const items = payload?.filter_column === "tahun" ? (payload.items || []).slice() : chartItems(payload);
  if (type === "donut") {
    return {
      color: chartPalette,
      textStyle: { fontFamily: DATA_FONT },
      tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      series: [{ type: "pie", radius: ["58%", "78%"], label: { show: false }, data: items.map((item) => ({ name: item.label, value: Number(item.total_anggaran || 0) })) }],
    };
  }
  return {
    color: ["#0f4c81"], textStyle: { fontFamily: DATA_FONT },
    grid: { left: 48, right: 24, top: 24, bottom: 44 },
    tooltip: { trigger: "axis", valueFormatter: (value) => rupiah(value) },
    xAxis: { type: "category", data: items.map((item) => item.label), axisLabel: { color: "rgba(65,71,83,.62)", fontFamily: DATA_FONT, fontWeight: 600 } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(26,28,29,.06)" } }, axisLabel: { formatter: (value) => compactRupiah(value) } },
    series: [{ type: "bar", data: items.map((item) => Number(item.total_anggaran || 0)), barMaxWidth: 120, itemStyle: { borderRadius: [8, 8, 0, 0], color: "#0f4c81" }, label: { show: true, position: "top", formatter: (params) => compactRupiah(params.value) } }],
  };
}

function renderCharts(charts) {
  if (!window.echarts || !charts) return;
  const targets = [
    ["anggaran_per_tahun", "chartTahunAnggaran", "bar"],
    ["komposisi_akun", "chartKualitas", "donut"],
  ];
  targets.forEach(([key, elementId, type]) => {
    const element = document.getElementById(elementId);
    const payload = charts[key];
    if (!element || !payload) return;
    state.charts[key]?.dispose();
    const chart = window.echarts.init(element);
    chart.setOption(chartOption(payload, type));
    chart.on("click", (params) => {
      if (payload.filter_column && params.name) {
        state.filters[payload.filter_column] = params.name;
        state.tableOffset = 0;
        loadDashboard();
      }
    });
    state.charts[key] = chart;
  });
}

function renderTrendNarrative(items) {
  const target = document.getElementById("trendNarrative");
  const top = chartItems({ items })[0];
  target.textContent = top ? `Tahun ${top.label} memiliki alokasi terbesar (${rupiah(top.total_anggaran)}).` : "Tidak ada data anggaran pada filter aktif.";
}

function renderYearSummary(items) {
  const target = document.getElementById("yearSummaryList");
  const rows = chartItems({ items });
  target.innerHTML = rows.length ? `<div class="year-summary-header"><span>Tahun</span><span>Anggaran</span><span>Item</span></div>${rows.map((item) => `<div class="year-summary-row"><span>${escapeHtml(item.label)}</span><span>Rp${escapeHtml(compactRupiah(item.total_anggaran))}</span><span>${number(item.jumlah_item || 0)}</span></div>`).join("")}` : `<div class="kpi-note">Tidak ada ringkasan tahun.</div>`;
}

function renderRankList(targetId, items, limit = 5) {
  const target = document.getElementById(targetId);
  if (!target) return;
  const rows = chartItems({ items }).slice(0, limit);
  const max = Math.max(...rows.map((item) => Number(item.total_anggaran || 0)), 1);
  target.innerHTML = rows.length ? rows.map((item) => {
    const amount = Number(item.total_anggaran || 0);
    return `<div class="rank-row"><div class="rank-row-header"><span>${escapeHtml(item.label)}</span><span>${compactRupiah(amount)}</span></div><div class="track"><div class="bar" style="width:${Math.max(4, Math.round(amount / max * 100))}%"></div></div></div>`;
  }).join("") : `<div class="kpi-note">Tidak ada data.</div>`;
}

function renderCluster(items) {
  const target = document.getElementById("clusterTreemap");
  if (!target) return;
  const rows = chartItems({ items }).slice(0, state.showAllClusters ? 12 : 4);
  target.innerHTML = rows.length ? rows.map((item) => `<button type="button" class="treemap-tile" data-cluster="${escapeHtml(item.label)}"><span class="treemap-title">${escapeHtml(item.label)}</span><span class="treemap-value">${compactRupiah(item.total_anggaran)}</span></button>`).join("") : `<div class="empty-state"><strong>Tidak ada kegiatan.</strong></div>`;
  target.querySelectorAll("[data-cluster]").forEach((button) => button.addEventListener("click", () => {
    state.filters.kegiatan = button.getAttribute("data-cluster");
    state.tableOffset = 0;
    loadDashboard();
  }));
}

function renderValidationRecap() {
  const target = document.getElementById("detailTable");
  const status = state.payload?.data?.summary?.status_rekonsiliasi || "NOT_AVAILABLE";
  target.innerHTML = `<div class="table-wrap validation-wrap"><table data-testid="local-validation-table"><thead><tr><th>Status</th><th>Dataset</th><th>Sumber</th></tr></thead><tbody><tr><td><span class="quality-pill">${escapeHtml(status)}</span></td><td>fact_anggaran</td><td>${escapeHtml(state.payload?.source || "-")}</td></tr></tbody></table></div>`;
}

function filteredRows(rows) {
  const term = state.tableSearch.trim().toLowerCase();
  return term ? rows.filter((row) => Object.values(row).some((value) => String(value ?? "").toLowerCase().includes(term))) : rows;
}

function renderTable(table) {
  const target = document.getElementById("detailTable");
  document.querySelectorAll("[data-tab]").forEach((button) => button.classList.toggle("active", button.getAttribute("data-tab") === state.activeTableTab));
  if (state.activeTableTab === "validasi") return renderValidationRecap();
  const rows = filteredRows(table?.rows || []);
  if (!rows.length) {
    target.innerHTML = `<div class="empty-state"><strong>Tidak ada baris detail.</strong><p>Ubah filter atau kata pencarian.</p></div>`;
    return;
  }
  const totalRows = Number(table.total_rows || 0);
  const offset = Number(table.offset || 0);
  const limit = Number(table.limit || state.tableLimit);
  target.innerHTML = `<div class="table-wrap"><table data-testid="local-detail-table"><thead><tr><th>Tahun</th><th>IKU</th><th>Kegiatan</th><th>Akun</th><th>Detail</th><th style="text-align:right">Anggaran</th><th>Status</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${escapeHtml(row.tahun)}</td><td class="primary-cell">${escapeHtml(row.iku)}</td><td class="strong-cell">${escapeHtml(row.kegiatan)}</td><td>${escapeHtml(row.akun)}</td><td class="truncate-cell">${escapeHtml(row.uraian_detail)}</td><td class="amount-cell">${plainRupiah(row.jumlah_weighted_iku)}</td><td><span class="quality-pill">${escapeHtml(row.mapping_status || "-")}</span></td></tr>`).join("")}</tbody></table></div><div class="table-footer"><span>Menampilkan <strong>${number(offset + 1)} - ${number(Math.min(offset + rows.length, totalRows))}</strong> dari ${number(totalRows)} baris</span><div class="pagination"><button type="button" class="pager-button" data-page="prev" ${offset > 0 ? "" : "disabled"}>‹</button><button type="button" class="pager-button" data-page="next" ${offset + limit < totalRows ? "" : "disabled"}>›</button></div></div>`;
  target.querySelectorAll("[data-page]").forEach((button) => button.addEventListener("click", () => {
    state.tableOffset = button.getAttribute("data-page") === "next" ? offset + limit : Math.max(0, offset - limit);
    loadDashboard();
  }));
}

function updateTitles(data) {
  const labels = data.labels || {};
  document.querySelector("h1").textContent = labels.title || "Dashboard Anggaran RAB/IKU";
  document.getElementById("dashboardSubtitle").innerHTML = escapeHtml(labels.subtitle || "Laporan tahunan dari Gold fact_anggaran.").replace("Gold fact_anggaran", "<strong>Gold fact_anggaran</strong>");
  const prodi = state.filters.prodi || "Semua Prodi";
  document.getElementById("prodiPill").innerHTML = `<span class="material-symbols-outlined" aria-hidden="true">school</span><span>Prodi: ${escapeHtml(prodi)}</span>`;
  document.getElementById("tableHeading").textContent = state.activeTableTab === "validasi" ? "Validasi Rekap" : "Detail Item Biaya";
  document.getElementById("tableSubtitle").textContent = state.activeTableTab === "validasi" ? "Status validasi laporan tahunan." : "Detail item anggaran pada filter aktif.";
}

function render() {
  const payload = state.payload || { status: "not_available", data: null };
  const data = payload.data || {};
  updateTitles(data);
  renderSource(payload);
  renderFilters(data.filters || {});
  renderActiveFilters();
  renderStatusPanel(payload);
  const ready = payload.status === "validated" || payload.status === "empty_after_filter";
  document.getElementById("kpiGrid").style.display = ready ? "grid" : "none";
  document.getElementById("dashboardGrid").style.display = ready ? "grid" : "none";
  if (!ready) return;
  renderKpis(data.summary);
  const yearly = data.charts?.anggaran_per_tahun?.items || [];
  renderTrendNarrative(yearly);
  renderYearSummary(data.charts?.ringkasan_per_tahun?.items || yearly);
  renderRankList("ikuRankList", data.charts?.anggaran_per_iku?.items || []);
  renderRankList("accountBudgetList", data.charts?.anggaran_per_akun?.items || [], 6);
  renderRankList("akunRankList", data.charts?.komposisi_akun?.items || [], 6);
  renderCluster(data.charts?.cluster_kegiatan?.items || []);
  renderTable(data.table);
  window.setTimeout(() => renderCharts(data.charts), 0);
}

function downloadTableCsv() {
  const rows = filteredRows(state.payload?.data?.table?.rows || []);
  if (!rows.length) return;
  const headers = ["tahun", "prodi", "iku", "kegiatan", "akun", "uraian_detail", "jumlah_weighted_iku", "mapping_status"];
  const lines = [headers.join(","), ...rows.map((row) => headers.map((key) => `"${String(row[key] ?? "").replace(/"/g, '""')}"`).join(","))];
  const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url; link.download = "silaras-dashboard-anggaran.csv"; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
}

document.getElementById("resetFilters").addEventListener("click", () => { state.filters = {}; state.tableOffset = 0; loadDashboard(); });
document.getElementById("refreshDashboard").addEventListener("click", () => loadDashboard());
document.getElementById("downloadCsv").addEventListener("click", downloadTableCsv);
document.getElementById("tableSearch").addEventListener("input", (event) => { state.tableSearch = event.target.value; renderTable(state.payload?.data?.table); });
document.getElementById("tablePageSize").addEventListener("change", (event) => { state.tableLimit = Number(event.target.value || 10); state.tableOffset = 0; loadDashboard(); });
document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => { state.activeTableTab = button.getAttribute("data-tab") || "detail"; updateTitles(state.payload?.data || {}); renderTable(state.payload?.data?.table); }));
window.addEventListener("resize", () => Object.values(state.charts).forEach((chart) => chart.resize()));
loadDashboard();
