/* ============================================================
   SILARAS SD — Dashboard Anggaran IKU (Superset mirror)
   Frontend logic. Data ditarik dari REST API Superset melalui
   proxy server-side (/api/dashboard/<id>/meta, /api/chart/...).
   Dashboard & tata letak dibangun dinamis dari Superset.
   ============================================================ */
"use strict";

(() => {
  const state = {
    meta: null,
    activeYear: null,           // null = "Semua"
    activeDashboardId: null,
    dashboards: [],
    charts: {},                 // chart_id -> { spec, payload }
    palette: ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)", "var(--chart-7)", "var(--chart-8)", "var(--chart-9)", "var(--chart-10)", "var(--chart-11)", "var(--chart-12)"],
    echarts: {},
    tables: {},                 // chart_id -> { page, size, search }
    sortOrder: {},              // chart_id -> "desc" | "asc" | null (default)
  };

  // Chart yang tidak relevan untuk tampilan bisnis (teknis pipeline/QA/redundant KPI) —
  // disaring dari grid, fetch, dan render. ID berlaku untuk dashboard #2 dan #3.
  const HIDDEN_CHART_IDS = new Set([
    19, // "Total Weighted IKU" — disembunyikan sesuai arahan pengguna
    27, // "Mapping Quality" — distribusi mapping_status (mapped_from_nomenklatur, review_queue, dll)
    29, // "Validasi Rekap" — rekap validasi file sumber & data_quality_flag
  ]);
  const isVisible = (spec) => !HIDDEN_CHART_IDS.has(spec.id) && !spec.title?.toLowerCase().includes("weighted iku");

  // Kolom yang ditampilkan untuk tabel line-item — hanya atribut bisnis,
  // urut disusun ulang (tanpa kolom teknis mapping_status/source_*).
  const TABLE_COLUMN_OVERRIDES = {
    28: ["tahun", "periode", "prodi", "iku", "kegiatan", "akun", "uraian_detail", "qty", "harga_satuan", "jumlah"],
  };

  // Label header yang lebih ramah untuk kolom snake_case.
  const TABLE_COLUMN_LABELS = {
    28: {
      tahun: "Tahun",
      periode: "Periode",
      prodi: "Prodi",
      iku: "IKU",
      kegiatan: "Kegiatan",
      akun: "Akun",
      uraian_detail: "Uraian Detail",
      qty: "Qty",
      harga_satuan: "Harga Satuan",
      jumlah: "Jumlah",
    },
  };

  const $ = (id) => document.getElementById(id);

  // -------------------------------------------------------------------------
  // Ikon inline SVG (Lucide-style) — pengganti Material Symbols font agar
  // setiap KPI/chart punya ikon yang berbeda & tajam di semua zoom/resolusi.
  // -------------------------------------------------------------------------
  const ICONS = {
    "arrow-left": '<path d="M19 12H5"/><path d="m12 19-7-7 7-7"/>',
    "arrow-up-down": '<path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/>',
    "arrow-down": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "arrow-up": '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    "bar-chart": '<line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
    "calendar-check": '<rect width="18" height="18" x="3" y="4" rx="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/><path d="m9 16 2 2 4-4"/>',
    "cloud-off": '<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/><path d="m2 2 20 20"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>',
    "grid": '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    "graduation-cap": '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "layout-dashboard": '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "moon": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "pie-chart": '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>',
    "refresh": '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    "table": '<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "wallet": '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
  };

  function svgIcon(name, size) {
    const body = ICONS[name] || ICONS["bar-chart"];
    return `<svg class="icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
  }

  // -------------------------------------------------------------------------
  // Formatting helpers
  // -------------------------------------------------------------------------
  const fmtInt = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 });
  const fmtRupiah = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0, maximumFractionDigits: 0 });

  function fmtCurrency(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "—";
    return fmtRupiah.format(Math.round(n));
  }

  function fmtNumber(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "—";
    return fmtInt.format(n);
  }

  function fmtCompactCurrency(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "—";
    const abs = Math.abs(n);
    if (abs >= 1e9) return "Rp " + (n / 1e9).toLocaleString("id-ID", { maximumFractionDigits: 2 }) + " M";
    if (abs >= 1e6) return "Rp " + (n / 1e6).toLocaleString("id-ID", { maximumFractionDigits: 2 }) + " jt";
    if (abs >= 1e3) return "Rp " + (n / 1e3).toLocaleString("id-ID", { maximumFractionDigits: 1 }) + " rb";
    return fmtRupiah.format(Math.round(n));
  }

  function formatValueForColumn(value, columnName) {
    const cn = columnName.toLowerCase();
    if (cn.includes("jumlah") || cn.includes("harga") || cn.includes("total") || cn === "qty") {
      const n = Number(value);
      if (!Number.isFinite(n)) return String(value ?? "");
      return cn === "qty" ? fmtNumber(n) : fmtCurrency(n);
    }
    if (typeof value === "number" && Number.isFinite(value)) return fmtInt.format(value);
    return String(value ?? "");
  }

  function cleanNumber(v) {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  }

  // -------------------------------------------------------------------------
  // Sort per kartu ("urutkan tertinggi/terendah").
  // Tiap chart/tabel punya tombol kecil di heading; klik memutar urutan:
  //   default -> terbesar (desc) -> terkecil (asc) -> default.
  // -------------------------------------------------------------------------
  const SORT_CYCLE = { null: "desc", desc: "asc", asc: null };

  function sortedRecords(chartId, records, valueKey) {
    const mode = state.sortOrder[chartId];
    if (!mode) return records;
    const arr = records.slice();
    arr.sort((a, b) => {
      const va = cleanNumber(a[valueKey]);
      const vb = cleanNumber(b[valueKey]);
      return mode === "desc" ? vb - va : va - vb;
    });
    return arr;
  }

  function nextSort(chartId) {
    state.sortOrder[chartId] = SORT_CYCLE[state.sortOrder[chartId] || "null"];
  }

  function sortButtonHTML(chartId) {
    const mode = state.sortOrder[chartId];
    let icon = "arrow-up-down";
    let title = "Urutkan nilai (terbesar / terkecil)";
    let active = false;
    if (mode === "desc") { icon = "arrow-down"; title = "Urut: terbesar ke terkecil"; active = true; }
    if (mode === "asc") { icon = "arrow-up"; title = "Urut: terkecil ke terbesar"; active = true; }
    return `<button type="button" class="sort-btn${active ? " active" : ""}" data-chart="${chartId}" title="${title}" aria-label="${title}">
      ${svgIcon(icon, 16)}
    </button>`;
  }

  function bindSortButton(container, chartId, onSort) {
    const btn = container.querySelector(`.sort-btn[data-chart="${chartId}"]`);
    if (!btn) return;
    btn.addEventListener("click", () => {
      nextSort(chartId);
      onSort();
      const holder = container.querySelector(`.sort-btn[data-chart="${chartId}"]`);
      if (holder) holder.outerHTML = sortButtonHTML(chartId);
      bindSortButton(container, chartId, onSort);
    });
  }

  // Subjudul ramah-bisnis per chart (penjelasan informatif & bebas pengulangan kata).
  function chartSubtitle(spec) {
    switch (spec.viz_type) {
      case "treemap_v2": return "Proporsi besaran anggaran berdasarkan rumpun kegiatan dan target IKU";
      case "pie": return "Persentase pembagian pos item biaya dalam struktur anggaran";
      case "echarts_timeseries_bar":
      case "bar":
        if (spec.dimension === "tahun") return "Tren alokasi dana dan estimasi proyeksi anggaran tahunan prodi";
        if (spec.dimension === "iku") return "Distribusi alokasi biaya berdasarkan Indikator Kinerja Utama (IKU)";
        return spec.orientation === "horizontal"
          ? "Peringkat akun belanja dengan penyerapan dana terbesar"
          : "Rincian alokasi dana per kategori jenis belanja & kode akun";
      case "big_number_total": return "";
      case "table": return spec.id === 28 ? "Daftar item biaya transaksional lengkap dengan filter & pencarian" : "Ringkasan agregat data keuangan prodi";
      default: return "";
    }
  }

  // -------------------------------------------------------------------------
  // Normalization: Superset dapat mengembalikan records atau [{"key","values"}]
  // -------------------------------------------------------------------------
  function toRecords(data) {
    if (!Array.isArray(data) || data.length === 0) return [];
    const first = data[0];
    if (first && Array.isArray(first.values) && (first.key !== undefined)) {
      const keys = Array.isArray(first.key) ? first.key : [first.key];
      return data.map((row) => {
        const rec = {};
        keys.forEach((k, i) => { rec[k] = row.key[i] ?? row.key; });
        (row.values || []).forEach((v) => { rec[v.colname ?? v.name] = v.value; });
        return rec;
      });
    }
    return data;
  }

  // -------------------------------------------------------------------------
  // Chart data plumbing
  // -------------------------------------------------------------------------
  function metricLabel(spec) {
    return spec.metric ? spec.metric.label : (spec.metrics && spec.metrics[0] ? spec.metrics[0].label : null);
  }

  function dimensionKey(spec) {
    return spec.dimension || (spec.groupby && spec.groupby[0]);
  }

  async function fetchJson(url) {
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) throw new Error(`HTTP ${res.status} — ${res.statusText}`);
    return res.json();
  }

  // -------------------------------------------------------------------------
  // Cache data chart (SWR-style) — "tampil dulu, re-fetch di belakang".
  // Payload disimpan di sessionStorage dengan key ber-versi; parsing aman
  // (try/catch). Payload lama yang rusak diperlakukan sebagai cache miss,
  // bukan error. Cache dibersihkan saat refresh paksa (force:true).
  // TTL menyamai cache server (60 detik): selama masih segar, tidak ada
  // re-fetch sama sekali — navigasi antar tahun/dashboard jadi instan.
  // -------------------------------------------------------------------------
  const CHART_CACHE_VERSION = "1";
  const CHART_CACHE_KEY = `silaras_dash_chart_cache_v${CHART_CACHE_VERSION}`;
  const CHART_CACHE_TTL_MS = 60 * 1000;
  const chartCache = new Map();

  function cacheKeyFor(chartId, year) {
    return `${state.activeDashboardId}:${chartId}:${year || "__all__"}`;
  }

  function chartCacheGet(chartId, year) {
    const k = cacheKeyFor(chartId, year);
    const entry = chartCache.get(k);
    if (!entry) return null;
    return { payload: entry.payload, fresh: Date.now() - entry.ts < CHART_CACHE_TTL_MS };
  }

  function chartCacheSet(chartId, year, payload) {
    if (!payload || payload.status !== "success") return;
    chartCache.set(cacheKeyFor(chartId, year), { ts: Date.now(), payload });
    try {
      sessionStorage.setItem(CHART_CACHE_KEY, JSON.stringify(Array.from(chartCache.entries())));
    } catch {}
  }

  function chartCacheLoad() {
    try {
      const raw = sessionStorage.getItem(CHART_CACHE_KEY);
      if (!raw) return;
      const entries = JSON.parse(raw);
      if (!Array.isArray(entries)) return;
      entries.forEach(([k, v]) => {
        if (v && v.payload && v.payload.status === "success") chartCache.set(k, v);
      });
    } catch {
      try { sessionStorage.removeItem(CHART_CACHE_KEY); } catch {}
    }
  }

  function chartCacheClear() {
    chartCache.clear();
    try { sessionStorage.removeItem(CHART_CACHE_KEY); } catch {}
  }

  async function loadChart(chartId, year, refresh) {
    const spec = state.meta.charts.find((c) => c.id === chartId);
    if (!refresh) {
      const cached = chartCacheGet(chartId, year);
      if (cached) {
        state.charts[chartId] = { spec, payload: cached.payload };
        // Cache lama (lewat TTL): tampilkan instan dulu, lalu re-fetch
        // di background agar data segar tanpa loading.
        if (!cached.fresh) refreshInBackground(chartId, year);
        return cached.payload;
      }
    }
    const payload = await fetchChartRemote(chartId, year, refresh);
    state.charts[chartId] = { spec, payload };
    chartCacheSet(chartId, year, payload);
    return payload;
  }

  async function fetchChartRemote(chartId, year, refresh) {
    const params = new URLSearchParams();
    if (year) params.set("tahun", year);
    params.set("dashboard", String(state.activeDashboardId));
    if (refresh) params.set("refresh", "1");
    return fetchJson(`/api/chart/${chartId}/data?${params.toString()}`);
  }

  function refreshInBackground(chartId, year) {
    fetchChartRemote(chartId, year, false)
      .then((payload) => {
        state.charts[chartId] = { ...state.charts[chartId], payload };
        chartCacheSet(chartId, year, payload);
        const spec = state.meta.charts.find((c) => c.id === chartId);
        renderChart(spec);
      })
      .catch(() => {});
  }

  async function loadAll(year, refresh) {
    const chartIds = state.meta.charts.filter(isVisible).map((c) => c.id);
    const results = await Promise.allSettled(chartIds.map((id) => loadChart(id, year, refresh)));
    const errors = [];
    results.forEach((r, i) => {
      const id = chartIds[i];
      const spec = state.meta.charts.find((c) => c.id === id);
      if (r.status === "rejected") {
        state.charts[id] = { spec, payload: { status: "unreachable", error: r.reason.message, chart_id: id, year } };
        errors.push(r.reason.message);
      } else if (r.value.status === "unreachable") {
        errors.push(r.value.error);
      }
    });
    return errors;
  }

  // -------------------------------------------------------------------------
  // Status / meta UI
  // -------------------------------------------------------------------------
  function setSourceStatus(kind, text) {
    const pill = $("sourceStatus");
    const dot = pill.querySelector(".status-dot");
    dot.className = "status-dot " + (kind === "ok" ? "ok" : kind === "err" ? "err" : "");
    pill.lastChild.textContent = " " + text;
  }

  function renderStatusPanel(errors) {
    const panel = $("statusPanel");
    if (!errors || errors.length === 0) {
      panel.className = "status-panel";
      panel.innerHTML = "";
      return;
    }
    panel.className = "status-panel visible";
    panel.innerHTML = `<div class="status-box">${svgIcon("cloud-off", 20)}<span>${errors.length} visualisasi gagal dimuat.</span></div>`;
  }

  function renderSourceInline() {
    const el = $("sourceInline");
    if (!state.meta) return;
    el.innerHTML = [
      `<span class="pill">Program Studi Sains Data</span>`,
      `<span class="pill">${state.meta.charts.filter(isVisible).length} visualisasi</span>`,
    ].join("");
  }

  // -------------------------------------------------------------------------
  // Dashboard selector
  // -------------------------------------------------------------------------
  async function loadDashboards() {
    const res = await fetchJson("/api/dashboards");
    state.dashboards = res.dashboards || [];
    const sel = $("dashboardSelect");
    sel.innerHTML = "";
    state.dashboards.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = String(d.id);
      opt.textContent = `#${d.id} — ${d.title}`;
      sel.appendChild(opt);
    });
    if (state.dashboards.length) {
      sel.value = String(state.activeDashboardId);
    }
  }

  let selectSeq = 0;
  async function selectDashboard(id) {
    const seq = ++selectSeq;
    state.activeDashboardId = Number(id);
    state.activeYear = null;
    $("dashboardSelect").value = String(id);
    state.meta = await fetchJson(`/api/dashboard/${id}/meta`);
    if (seq !== selectSeq) return;
    renderSourceInline();
    renderYearTabs();
    renderActiveFilters();
    buildDashboardGrid();
    await refreshDashboard(false, seq);
  }

  // -------------------------------------------------------------------------
  // Year tabs
  // -------------------------------------------------------------------------
  function renderYearTabs() {
    const tabs = $("yearTabs");
    tabs.innerHTML = "";
    const options = (state.meta && state.meta.year_options) || ["Semua"];
    options.forEach((opt) => {
      const isActive = opt === "Semua" ? state.activeYear === null : String(state.activeYear) === String(opt);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "year-tab" + (isActive ? " active" : "");
      btn.textContent = opt;
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-selected", String(isActive));
      btn.dataset.year = opt === "Semua" ? "" : opt;
      btn.addEventListener("click", () => selectYear(opt === "Semua" ? null : opt));
      tabs.appendChild(btn);
    });
  }

  function renderActiveFilters() {
    $("activeFilters").textContent = state.activeYear ? `Menampilkan data tahun: ${state.activeYear}` : "Menampilkan data semua tahun";
  }

  async function selectYear(year) {
    const seq = ++selectSeq;
    state.activeYear = year;
    renderYearTabs();
    renderActiveFilters();
    await refreshDashboard(false, seq);
  }

  // -------------------------------------------------------------------------
  // Dynamic grid building
  // -------------------------------------------------------------------------
  // Ikon per-metrik KPI — tiap kartu dapat ikon berbeda & bermakna.
  // Dipetakan per chart id (dashboard #2 dan #3 berbagi id yang sama).
  const METRIC_ICONS = {
    18: "wallet",         // Total Anggaran
    19: "target",         // Total Weighted IKU
    20: "layers",         // Jumlah Item
    21: "flag",           // Jumlah IKU
    22: "calendar-check", // Jumlah Kegiatan
  };

  function metricIcon(spec) {
    return METRIC_ICONS[spec.id] || "bar-chart";
  }

  function chartIcon(spec) {
    switch (spec.viz_type) {
      case "table": return "table";
      case "pie": return "pie-chart";
      case "treemap_v2": return "grid";
      case "echarts_timeseries_bar":
      case "bar": return "bar-chart";
      default: return "bar-chart";
    }
  }

  function buildDashboardGrid() {
    const kpiGrid = $("kpiGrid");
    const dashGrid = $("dashboardGrid");
    kpiGrid.innerHTML = "";
    dashGrid.innerHTML = "";
    state.tables = {};
    state.echarts = {};

    const charts = state.meta.charts.filter(isVisible);
    charts.forEach((spec, idx) => {
      if (spec.section === "kpi" || spec.viz_type === "big_number_total") {
        const card = document.createElement("div");
        card.className = "metric-card";
        card.dataset.chartId = String(spec.id);
        card.innerHTML = `
          <div class="metric-top">
            <span class="metric-icon-box">${svgIcon(metricIcon(spec), 20)}</span>
            <span class="metric-label">${escapeHtml(spec.title)}</span>
          </div>
          <div class="metric-value" id="kpiValue${spec.id}"><span class="chart-empty" style="min-height:0;padding:0">Memuat…</span></div>
          <div class="metric-footer" id="kpiFoot${spec.id}">Menunggu data…</div>`;
        kpiGrid.appendChild(card);
        return;
      }

      if (spec.viz_type === "table") {
        const card = document.createElement("article");
        card.className = "glass-card table-card span-2";
        card.dataset.chartId = String(spec.id);
        const cols = tableColumns(spec);
        card.innerHTML = `
          <div class="table-header">
            <div class="table-title-row">
              <span class="table-title-icon">${svgIcon("table", 18)}</span>
              <div>
                <h2>${escapeHtml(spec.title)}</h2>
                <p id="tblSub${spec.id}">${escapeHtml(chartSubtitle(spec))} · ${cols.length} kolom.</p>
              </div>
            </div>
            <div class="table-actions">
              ${sortButtonHTML(spec.id)}
              <label class="search-box">
                ${svgIcon("search", 16)}
                <input id="tblSearch${spec.id}" type="search" placeholder="Cari data..." autocomplete="off">
              </label>
              <label class="page-size">
                <span>Rows</span>
                <select id="tblSize${spec.id}" aria-label="Jumlah baris tabel">
                  <option value="10" selected>10 data</option>
                  <option value="20">20 data</option>
                  <option value="50">50 data</option>
                </select>
              </label>
            </div>
          </div>
          <div class="table-wrapper" id="tblWrap${spec.id}"></div>
          <div class="pagination-row" id="tblPag${spec.id}"></div>`;
        dashGrid.appendChild(card);
        state.tables[spec.id] = { page: 0, size: 10, search: "" };
        $(`tblSearch${spec.id}`).addEventListener("input", (e) => {
          state.tables[spec.id].page = 0;
          state.tables[spec.id].search = e.target.value.trim().toLowerCase();
          renderTable(spec.id);
        });
        $(`tblSize${spec.id}`).addEventListener("change", (e) => {
          state.tables[spec.id].size = Number(e.target.value);
          state.tables[spec.id].page = 0;
          renderTable(spec.id);
        });
        bindSortButton(card, spec.id, () => renderTable(spec.id));
        return;
      }

      // analytics charts
      const card = document.createElement("article");
      const isTreemap = spec.viz_type === "treemap_v2";
      const isPie = spec.viz_type === "pie";
      card.className = "glass-card chart-card" + (isTreemap || isPie ? " span-2" : "");
      card.dataset.chartId = String(spec.id);
      const subtitle = chartSubtitle(spec);
      const heading = `
        <div class="card-heading">
          <div class="card-heading-icon">${svgIcon(chartIcon(spec), 18)}</div>
          <div class="card-heading-text">
            <h2>${escapeHtml(spec.title)}</h2>
            ${subtitle ? `<p>${escapeHtml(subtitle)}</p>` : ""}
          </div>
          ${sortButtonHTML(spec.id)}
        </div>`;
      if (isPie) {
        card.innerHTML = `
          ${heading}
          <div class="donut-layout">
            <div class="chart donut-chart" id="chart${spec.id}" data-chart-id="${spec.id}"></div>
            <div class="legend-list" id="legend${spec.id}"></div>
          </div>`;
      } else {
        const heightClass = isTreemap ? "chart-treemap" : (spec.dimension === "tahun" ? "chart-large" : "chart-medium chart-scroll");
        card.innerHTML = `
          ${heading}
          <div class="chart ${heightClass}" id="chart${spec.id}" data-chart-id="${spec.id}"></div>`;
      }
      dashGrid.appendChild(card);
      bindSortButton(card, spec.id, () => renderChart(spec));
    });
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // -------------------------------------------------------------------------
  // Rendering: KPIs
  // -------------------------------------------------------------------------
  function chartRecords(id) {
    const chartId = Number(String(id).replace("chart", ""));
    const payload = state.charts[chartId]?.payload;
    if (!payload || payload.status !== "success") return null;
    return toRecords(payload.data);
  }

  function renderKpis() {
    state.meta.charts.filter(isVisible).forEach((spec) => {
      if (!(spec.viz_type === "big_number_total")) return;
      const payload = state.charts[spec.id]?.payload;
      const records = payload && payload.status === "success" ? toRecords(payload.data) : [];
      const ok = payload && payload.status === "success";
      const label = metricLabel(spec);
      let value = null;
      if (ok && records.length) {
        const row = records[0];
        value = row[label] !== undefined && row[label] !== null ? row[label] : Object.values(row).find((v) => typeof v === "number");
      }
      const valEl = $(`kpiValue${spec.id}`);
      const footEl = $(`kpiFoot${spec.id}`);
      if (!valEl || !footEl) return;
      if (ok && value !== null && value !== undefined) {
        valEl.textContent = spec.value_format === "currency" ? fmtCurrency(value) : fmtNumber(value);
        footEl.textContent = state.activeYear ? `Anggaran tahun ${state.activeYear}` : "Akumulasi semua tahun";
      } else if (!ok) {
        valEl.innerHTML = "<span style='color:var(--state-error)'>Gagal</span>";
        footEl.textContent = payload?.error ? `Error: ${payload.error}` : "Menunggu data…";
      }
    });
  }

  // -------------------------------------------------------------------------
  // Rendering: ECharts helpers
  // -------------------------------------------------------------------------
  function getChart(elId) {
    const el = $(elId);
    if (!el) return null;
    let chart = echarts.getInstanceByDom(el);
    if (!chart) {
      // Supersampling: render canvas pada pixel ratio >= 2 supaya label/angka
      // di dalam chart tampil tajam ("hd"), tidak burik di layar HiDPI maupun normal.
      const pixelRatio = Math.max(window.devicePixelRatio || 1, 2);
      chart = echarts.init(el, null, { renderer: "canvas", devicePixelRatio: pixelRatio });
    }
    state.echarts[elId] = chart;
    // Canvas ECharts tidak menyesuaikan diri otomatis saat flexbox/grid
    // mengubah ukuran kontainer (mis. kartu diregangkan ke tinggi baris) —
    // pantau ukuran kontainer dan panggil resize() agar chart selalu mengisi kartu.
    if (!el.dataset.observerAttached) {
      el.dataset.observerAttached = "1";
      if (typeof ResizeObserver !== "undefined") {
        const ro = new ResizeObserver(() => {
          const c = state.echarts[elId];
          if (c) c.resize();
        });
        ro.observe(el);
      }
    }
    return chart;
  }

  function makeChart(elId, option) {
    const chart = getChart(elId);
    if (!chart) return;
    chart.setOption(resolveTokens(option), true);
    return chart;
  }

  // ECharts canvas tidak mendukung CSS custom properties — resolve "var(--x)"
  // ke nilai nyata dari computed style agar tooltip/label mengikuti tema aktif.
  function resolveTokens(node) {
    if (typeof node === "string") {
      return node.replace(/var\(\s*(--[a-z0-9-]+)\s*\)/gi, (m, name) => {
        const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || m;
      });
    }
    if (Array.isArray(node)) return node.map(resolveTokens);
    if (node && typeof node === "object") {
      const out = {};
      for (const key of Object.keys(node)) out[key] = resolveTokens(node[key]);
      return out;
    }
    return node;
  }

  function baseTooltip(currency) {
    return {
      trigger: "axis",
      backgroundColor: "var(--surface-glass-solid)",
      borderColor: "var(--surface-glass-border)",
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: "var(--text-primary)", fontSize: 12 },
      formatter: (params) => {
        if (!Array.isArray(params)) params = [params];
        return params.map((p) => {
          const name = p.axisValueLabel ?? p.name ?? "";
          const row = p.data && typeof p.data === "object" ? p.data : null;
          const raw = row ? (row.raw ?? row.value) : p.value;
          return `<div style="font-weight:700">${escapeHtml(String(name))}</div><div style="margin-top:4px">${currency ? fmtCurrency(Number(raw)) : fmtNumber(Number(raw))}</div>`;
        }).join("");
      },
    };
  }

  function emptyChart(elId) {
    const el = $(elId);
    if (el) el.innerHTML = '<div class="chart-empty">Tidak ada data untuk filter ini.</div>';
  }

  function renderBar(spec, horizontal) {
    const elId = `chart${spec.id}`;
    const records = chartRecords(spec.id);
    if (!records || records.length === 0) {
      emptyChart(elId);
      return;
    }
    const el = $(elId);
    const dimKey = dimensionKey(spec) || Object.keys(records[0])[0];
    const metKey = metricLabel(spec) || Object.keys(records[0]).find((k) => typeof records[0][k] === "number");
    if (!dimKey || !metKey) {
      emptyChart(elId);
      return;
    }

    const sorted = sortedRecords(spec.id, records, metKey);
    const cats = sorted.map((r) => String(r[dimKey] ?? ""));
    const vals = sorted.map((r) => cleanNumber(r[metKey]));
    const currency = spec.value_format === "currency";
    const full = records.length;

    const isH = horizontal || spec.orientation === "horizontal";
    if (isH) {
      el.style.height = Math.max(220, Math.min(520, full * 34 + 90)) + "px";
    } else {
      el.style.height = "";
      el.classList.remove("chart-medium", "chart-scroll", "chart-large", "chart-treemap");
      el.classList.add(full > 12 ? "chart-tall" : "chart-large");
    }

    const rows = sorted.map((r, i) => ({ name: String(r[dimKey] ?? ""), value: vals[i] }));

    makeChart(elId, {
      animationDuration: 500,
      color: [state.palette[0]],
      grid: isH
        ? { left: 8, right: 70, top: 16, bottom: 8, containLabel: true }
        : { left: 8, right: 16, top: 20, bottom: 8, containLabel: true },
      tooltip: baseTooltip(currency),
      xAxis: isH
        ? { type: "value", axisLabel: { color: "var(--text-tertiary)", fontSize: 11, formatter: (v) => fmtCompactCurrency(v) }, splitLine: { lineStyle: { color: "var(--surface-glass-border)", type: "dashed" } } }
        : { type: "category", data: cats, axisLabel: { color: "var(--text-tertiary)", fontSize: 11, rotate: cats.length > 6 ? 30 : 0, formatter: (v) => (v.length > 16 ? v.slice(0, 15) + "…" : v) }, axisLine: { lineStyle: { color: "var(--surface-glass-border)" } } },
      yAxis: isH
        ? { type: "category", data: cats, axisLabel: { color: "var(--text-secondary)", fontSize: 11, width: 180, overflow: "truncate" }, axisLine: { show: false }, axisTick: { show: false } }
        : { type: "value", axisLabel: { color: "var(--text-tertiary)", fontSize: 11, formatter: (v) => fmtCompactCurrency(v) }, splitLine: { lineStyle: { color: "var(--surface-glass-border)", type: "dashed" } } },
      series: [{
        type: "bar",
        data: rows,
        barMaxWidth: isH ? 20 : 42,
        itemStyle: { borderRadius: isH ? [0, 8, 8, 0] : [8, 8, 0, 0], color: { type: "linear", x: 0, y: 0, x2: isH ? 1 : 0, y2: isH ? 0 : 1, colorStops: [{ offset: 0, color: "#0a84ff" }, { offset: 1, color: "#0071e3" }] } },
        label: {
          show: true,
          position: isH ? "right" : "top",
          color: "var(--text-secondary)",
          fontSize: 10,
          fontWeight: 600,
          formatter: (p) => (currency ? fmtCompactCurrency(p.value) : fmtNumber(p.value)),
        },
      }],
    });
  }

  function renderTreemap(spec) {
    const elId = `chart${spec.id}`;
    const records = chartRecords(spec.id);
    if (!records || records.length === 0) {
      emptyChart(elId);
      return;
    }
    const [topKey, childKey] = spec.groupby;
    const metKey = metricLabel(spec);
    if (!topKey || !metKey) {
      emptyChart(elId);
      return;
    }

    // Batasi jumlah node agar treemap tetap bersih: maksimal 10 grup IKU
    // dan 8 kegiatan per IKU; sisanya digabung ke "… lainnya".
    const MAX_GROUPS = 10;
    const MAX_CHILDREN = 8;

    const groupMap = new Map();
    records.forEach((r) => {
      const top = String(r[topKey] ?? "—");
      const child = String(r[childKey] ?? "—");
      const val = cleanNumber(r[metKey]);
      if (!groupMap.has(top)) groupMap.set(top, new Map());
      const childMap = groupMap.get(top);
      childMap.set(child, (childMap.get(child) || 0) + val);
    });

    let groups = Array.from(groupMap.entries()).map(([name, childMap]) => {
      const children = Array.from(childMap.entries())
        .map(([n, value]) => ({ name: n, value }))
        .sort((a, b) => b.value - a.value);
      const value = children.reduce((s, c) => s + c.value, 0);
      if (children.length > MAX_CHILDREN) {
        const keep = children.slice(0, MAX_CHILDREN);
        const rest = children.slice(MAX_CHILDREN).reduce((s, c) => s + c.value, 0);
        keep.push({ name: "Kegiatan lainnya", value: rest });
        children.splice(0, children.length, ...keep);
      }
      return { name, value, children };
    });

    const order = state.sortOrder[spec.id];
    if (order) {
      groups.sort((a, b) => order === "desc" ? b.value - a.value : a.value - b.value);
    }
    let data;
    if (groups.length > MAX_GROUPS) {
      const keep = groups.slice(0, MAX_GROUPS);
      const rest = groups.slice(MAX_GROUPS).reduce((s, g) => s + g.value, 0);
      keep.push({ name: "IKU lainnya", value: rest, children: [] });
      data = keep;
    } else {
      data = groups;
    }
    data = data.map((t, i) => ({ ...t, itemStyle: { color: state.palette[i % state.palette.length] } }));

    makeChart(elId, {
      animationDuration: 400,
      animationDurationUpdate: 400,
      tooltip: {
        confine: true,
        backgroundColor: "var(--surface-glass-solid)",
        borderColor: "var(--surface-glass-border)",
        textStyle: { color: "var(--text-primary)", fontSize: 12 },
        formatter: (p) => {
          const info = p.treePathInfo || [];
          const parent = info.length > 1 && info[info.length - 2] ? info[info.length - 2].name : null;
          const label = parent && parent !== p.name ? `${parent} · ${p.name}` : p.name;
          return `<div style="font-weight:700">${escapeHtml(label)}</div><div style="margin-top:4px">${fmtCurrency(cleanNumber(p.value))}</div>`;
        },
      },
      series: [{
        type: "treemap",
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        visibleMin: 6,
        label: {
          show: true,
          color: "#fff",
          fontSize: 11,
          fontWeight: 600,
          formatter: (p) => {
            const name = String(p.name || "");
            const short = name.length > 22 ? name.slice(0, 21) + "…" : name;
            return `${short}\n${fmtCompactCurrency(p.value)}`;
          },
        },
        upperLabel: { show: true, height: 24, color: "#fff", fontSize: 11, fontWeight: 700, textBorderColor: "transparent" },
        itemStyle: { borderColor: "var(--surface-glass-solid)", borderWidth: 2, gapWidth: 2, borderRadius: 6 },
        levels: [
          { itemStyle: { borderColor: "var(--surface-glass-solid)", borderWidth: 2, gapWidth: 2, borderRadius: 6 } },
          { colorMappingBy: "value", colorSaturation: [0.35, 0.7], itemStyle: { borderWidth: 1, gapWidth: 1 } },
        ],
        data,
      }],
    });
  }

  function renderDonut(spec) {
    const elId = `chart${spec.id}`;
    const legend = $(`legend${spec.id}`);
    const records = chartRecords(spec.id);
    if (!records || records.length === 0) {
      emptyChart(elId);
      if (legend) legend.innerHTML = "";
      return;
    }
    const dimKey = dimensionKey(spec) || Object.keys(records[0])[0];
    const metKey = metricLabel(spec) || Object.keys(records[0]).find((k) => typeof records[0][k] === "number");
    if (!dimKey || !metKey) {
      emptyChart(elId);
      if (legend) legend.innerHTML = "";
      return;
    }

    const sorted = sortedRecords(spec.id, records, metKey);
    const data = sorted.map((r) => ({ name: String(r[dimKey] ?? "—"), value: cleanNumber(r[metKey]) }));
    const total = data.reduce((s, d) => s + d.value, 0) || 1;

    makeChart(elId, {
      animationDuration: 500,
      color: state.palette,
      tooltip: {
        trigger: "item",
        backgroundColor: "var(--surface-glass-solid)",
        borderColor: "var(--surface-glass-border)",
        textStyle: { color: "var(--text-primary)", fontSize: 12 },
        formatter: (p) => `<div style="font-weight:700">${escapeHtml(p.name)}</div><div style="margin-top:4px">${fmtNumber(p.value)} (${((p.value / total) * 100).toFixed(1)}%)</div>`,
      },
      series: [{
        type: "pie",
        radius: ["46%", "72%"],
        center: ["50%", "50%"],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 8, borderColor: "var(--surface-glass-solid)", borderWidth: 2 },
        label: { show: true, color: "var(--text-secondary)", fontSize: 11, formatter: "{d}%" },
        labelLine: { length: 8, length2: 6, lineStyle: { color: "var(--surface-glass-border)" } },
        data,
      }],
    });

    if (legend) {
      legend.innerHTML = data.map((d, i) => `
        <div class="legend-item">
          <span class="legend-swatch" style="background:${state.palette[i % state.palette.length]}"></span>
          <span class="li-name">${escapeHtml(d.name)}</span>
          <span class="li-val">${fmtNumber(d.value)}</span>
        </div>`).join("");
    }
  }

  // -------------------------------------------------------------------------
  // Rendering: tables
  // -------------------------------------------------------------------------
  function tableColumns(spec) {
    if (TABLE_COLUMN_OVERRIDES[spec.id]) return TABLE_COLUMN_OVERRIDES[spec.id];
    if (spec.columns && spec.columns.length) return spec.columns;
    if (spec.groupby && spec.groupby.length) {
      return [...spec.groupby, ...((spec.metrics || []).map((m) => m.label))];
    }
    return [];
  }

  function renderTable(id) {
    const wrap = $(`tblWrap${id}`);
    const pag = $(`tblPag${id}`);
    const records = chartRecords(id);
    const st = state.tables[id];
    if (!st) return;
    if (!records || records.length === 0) {
      if (wrap) wrap.innerHTML = '<table class="apple-table"><tbody><tr class="tbl-empty"><td>Tidak ada data untuk filter ini.</td></tr></tbody></table>';
      if (pag) pag.innerHTML = "";
      const sub = $(`tblSub${id}`);
      if (sub) sub.textContent = "0 baris — tidak ada data untuk filter aktif.";
      return;
    }

    const spec = state.meta.charts.find((c) => c.id === id);
    const cols = tableColumns(spec);
    let rows = records;
    if (st.search) {
      rows = rows.filter((r) => cols.some((c) => String(r[c] ?? "").toLowerCase().includes(st.search)));
    }
    const mode = state.sortOrder[id];
    if (mode) {
      const sortCol = cols.find((c) => /jumlah|harga|total|qty/.test(c.toLowerCase())) || cols[0];
      rows = rows.slice().sort((a, b) => {
        const va = cleanNumber(a[sortCol]);
        const vb = cleanNumber(b[sortCol]);
        if (va !== vb) return mode === "desc" ? vb - va : va - vb;
        return 0;
      });
    }
    const totalPages = Math.max(1, Math.ceil(rows.length / st.size));
    if (st.page >= totalPages) st.page = totalPages - 1;
    const pageRows = rows.slice(st.page * st.size, st.page * st.size + st.size);

    const header = cols.map((c) => {
      const lower = c.toLowerCase();
      const numeric = lower.includes("jumlah") || lower.includes("harga") || lower.includes("total") || c === "qty";
      const label = (TABLE_COLUMN_LABELS[spec.id] && TABLE_COLUMN_LABELS[spec.id][c]) || c;
      return `<th class="${numeric ? "num" : ""}">${escapeHtml(String(label))}</th>`;
    }).join("");

    const body = pageRows.map((r) => {
      let quality = r["data_quality_flag"];
      let badge = "";
      if (quality !== undefined && quality !== null && quality !== "") {
        const q = String(quality).toLowerCase();
        const cls = q.includes("ok") || q.includes("pass") || q.includes("valid") ? "badge badge-ok" : q.includes("warn") ? "badge badge-warn" : "badge badge-err";
        badge = `<span class="${cls}">${escapeHtml(String(quality))}</span>`;
      }
      let mapping = r["mapping_status"];
      let mapCell = escapeHtml(String(mapping ?? ""));
      if (mapping !== undefined && mapping !== null && mapping !== "") {
        const m = String(mapping).toLowerCase();
        const cls = m.includes("mapped") || m.includes("ok") || m.includes("passed") ? "badge badge-ok" : "badge badge-warn";
        mapCell = `<span class="${cls}">${escapeHtml(String(mapping))}</span>`;
      }
      return "<tr>" + cols.map((c) => {
        if (c === "data_quality_flag") return `<td>${badge}</td>`;
        if (c === "mapping_status") return `<td>${mapCell}</td>`;
        const v = r[c];
        const lower = c.toLowerCase();
        const numeric = lower.includes("jumlah") || lower.includes("harga") || lower.includes("total") || c === "qty";
        return `<td class="${numeric ? "num" : ""}">${escapeHtml(formatValueForColumn(v, c))}</td>`;
      }).join("") + "</tr>";
    }).join("");

    if (wrap) wrap.innerHTML = `<table class="apple-table"><thead><tr>${header}</tr></thead><tbody>${body || '<tr class="tbl-empty"><td>Pencarian tidak menemukan hasil.</td></tr>'}</tbody></table>`;

    const sub = $(`tblSub${id}`);
    if (sub) sub.textContent = `${fmtInt.format(records.length)} baris${st.search ? ` — ${fmtInt.format(rows.length)} hasil pencarian` : ""}.`;

    if (pag) {
      pag.innerHTML = `
        <span>Hal ${st.page + 1} dari ${totalPages} · ${fmtInt.format(rows.length)} baris</span>
        <div class="page-buttons">
          <button type="button" data-table="${id}" data-dir="-1" ${st.page === 0 ? "disabled" : ""}>Sebelumnya</button>
          <button type="button" data-table="${id}" data-dir="1" ${st.page >= totalPages - 1 ? "disabled" : ""}>Berikutnya</button>
        </div>`;
      pag.querySelectorAll("button").forEach((btn) => btn.addEventListener("click", () => {
        state.tables[id].page += Number(btn.dataset.dir);
        renderTable(id);
      }));
    }
  }

  // -------------------------------------------------------------------------
  // Render everything
  // -------------------------------------------------------------------------
  function renderChart(spec) {
    if (spec.viz_type === "big_number_total") {
      renderKpis();
      return;
    }
    if (spec.viz_type === "table") {
      renderTable(spec.id);
      return;
    }
    if (spec.viz_type === "treemap_v2") {
      renderTreemap(spec);
    } else if (spec.viz_type === "pie") {
      renderDonut(spec);
    } else if (spec.viz_type === "echarts_timeseries_bar" || spec.viz_type === "bar") {
      renderBar(spec, spec.dimension === "iku");
    }
  }

  function renderDashboard(errors) {
    renderKpis();
    state.meta.charts.filter(isVisible).forEach(renderChart);
    renderStatusPanel(errors);
    const anyFail = errors.length > 0;
    setSourceStatus(anyFail ? "warn" : "ok", anyFail ? `${errors.length} visualisasi gagal dimuat` : "Data terhubung");
    $("footerStatus").textContent = anyFail ? `${errors.length} visualisasi bermasalah` : "Semua data berhasil dimuat";
  }

  async function refreshDashboard(force, seq = selectSeq) {
    const btn = $("refreshDashboard");
    btn.classList.add("spinning");
    btn.disabled = true;
    try {
      if (force) chartCacheClear();
      const errors = await loadAll(state.activeYear, force);
      if (seq !== selectSeq) return;
      renderDashboard(errors);
      if (force) showToast("Data berhasil dimuat ulang");
    } catch (err) {
      if (seq !== selectSeq) return;
      setSourceStatus("err", "Gagal memuat data");
      $("footerStatus").textContent = "Gagal memuat data";
      renderStatusPanel([err.message]);
    } finally {
      btn.classList.remove("spinning");
      btn.disabled = false;
    }
  }

  // -------------------------------------------------------------------------
  // Theme (Terang / Gelap — mengikuti pola portal v2)
  // -------------------------------------------------------------------------
  function applyThemeUI(theme) {
    const lightBtn = $("themeBtnLight");
    const darkBtn = $("themeBtnDark");
    if (lightBtn) lightBtn.classList.toggle("active", theme === "light");
    if (darkBtn) darkBtn.classList.toggle("active", theme === "dark");
    document.documentElement.setAttribute("data-theme", theme);
  }

  function setTheme(theme) {
    if (theme !== "light" && theme !== "dark") theme = "light";
    state.theme = theme;
    applyThemeUI(theme);
    try {
      localStorage.setItem("silaras_dash_theme", theme);
    } catch {}
    // Re-render chart supaya warna ECharts mengikuti tema (tanpa re-fetch data).
    renderDashboard([]);
  }

  // -------------------------------------------------------------------------
  // Toast
  // -------------------------------------------------------------------------
  let toastTimer = null;
  function showToast(text) {
    $("toastText").textContent = text;
    const t = $("appToast");
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
  }

  // -------------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------------
  function bindEvents() {
    $("refreshDashboard").addEventListener("click", () => refreshDashboard(true));
    $("dashboardSelect").addEventListener("change", (e) => selectDashboard(e.target.value));
    $("themeBtnLight").addEventListener("click", () => setTheme("light"));
    $("themeBtnDark").addEventListener("click", () => setTheme("dark"));
    window.addEventListener("resize", () => {
      Object.values(state.echarts).forEach((ch) => ch.resize());
    });
  }

  async function init() {
    state.theme = "light";
    try {
      const saved = localStorage.getItem("silaras_dash_theme");
      if (saved === "dark" || saved === "light") state.theme = saved;
    } catch {}
    chartCacheLoad();
    applyThemeUI(state.theme);
    bindEvents();
    try {
      await loadDashboards();
      state.activeDashboardId = state.dashboards[0] ? state.dashboards[0].id : 2;
      await selectDashboard(state.activeDashboardId);
    } catch (err) {
      setSourceStatus("err", "Gagal memuat data");
      $("footerStatus").textContent = "Gagal memuat data";
      renderStatusPanel([err.message]);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
