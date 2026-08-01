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
    palette: ["#0071e3", "#34c759", "#ff9f0a", "#ff453a", "#5856d6", "#af52de", "#ff2d55", "#64d2ff", "#5ac8fa", "#a2845e", "#b8e986", "#ffd60a"],
    echarts: {},
    tables: {},                 // chart_id -> { page, size, search }
  };

  const $ = (id) => document.getElementById(id);

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
    const n = Number(value);
    if (!Number.isFinite(n)) return String(value ?? "");
    const cn = columnName.toLowerCase();
    if (cn.includes("jumlah") || cn.includes("harga") || cn.includes("total")) return fmtCurrency(n);
    return fmtInt.format(n);
  }

  function cleanNumber(v) {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
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

  async function loadChart(chartId, year, refresh) {
    const spec = state.meta.charts.find((c) => c.id === chartId);
    const params = new URLSearchParams();
    if (year) params.set("tahun", year);
    params.set("dashboard", String(state.activeDashboardId));
    if (refresh) params.set("refresh", "1");
    const payload = await fetchJson(`/api/chart/${chartId}/data?${params.toString()}`);
    state.charts[chartId] = { spec, payload };
    return payload;
  }

  async function loadAll(year, refresh) {
    const chartIds = state.meta.charts.map((c) => c.id);
    const results = await Promise.allSettled(chartIds.map((id) => loadChart(id, year, refresh)));
    const errors = [];
    results.forEach((r, i) => {
      const id = chartIds[i];
      const spec = state.meta.charts.find((c) => c.id === id);
      if (r.status === "rejected") {
        state.charts[id] = { spec, payload: { status: "unreachable", error: r.reason.message, chart_id: id, year } };
        errors.push(`chart #${id}: ${r.reason.message}`);
      } else if (r.value.status === "unreachable") {
        errors.push(`chart #${id}: ${r.value.error}`);
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
    panel.innerHTML = `<div class="status-box"><span class="material-symbols-outlined" aria-hidden="true">cloud_off</span><span>${errors.length} chart gagal dimuat dari Superset.</span></div>`;
  }

  function renderSourceInline() {
    const el = $("sourceInline");
    if (!state.meta) return;
    el.innerHTML = [
      `<span class="pill">Sumber: Superset API v1</span>`,
      `<span class="pill">Dashboard #${state.meta.dashboard_id}</span>`,
      `<span class="pill">${state.meta.chart_count} chart</span>`,
      `<span class="pill">Data via proxy server — tanpa akses DB langsung</span>`,
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

  async function selectDashboard(id) {
    state.activeDashboardId = Number(id);
    state.activeYear = null;
    $("dashboardSelect").value = String(id);
    state.meta = await fetchJson(`/api/dashboard/${id}/meta`);
    renderSourceInline();
    renderYearTabs();
    renderActiveFilters();
    buildDashboardGrid();
    await refreshDashboard(false);
  }

  // -------------------------------------------------------------------------
  // Year tabs
  // -------------------------------------------------------------------------
  function renderYearTabs() {
    const tabs = $("yearTabs");
    tabs.innerHTML = "";
    const options = (state.meta && state.meta.year_options) || ["Semua"];
    options.forEach((opt) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "year-tab" + (state.activeYear === null && opt === "Semua" ? " active" : "");
      btn.textContent = opt;
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-selected", String(state.activeYear === null && opt === "Semua"));
      btn.dataset.year = opt === "Semua" ? "" : opt;
      btn.addEventListener("click", () => selectYear(opt === "Semua" ? null : opt));
      tabs.appendChild(btn);
    });
  }

  function renderActiveFilters() {
    $("activeFilters").textContent = state.activeYear ? `Menampilkan data tahun: ${state.activeYear}` : "Menampilkan data semua tahun";
  }

  async function selectYear(year) {
    state.activeYear = year;
    renderYearTabs();
    renderActiveFilters();
    await refreshDashboard(false);
  }

  // -------------------------------------------------------------------------
  // Dynamic grid building
  // -------------------------------------------------------------------------
  function chartIcon(spec) {
    switch (spec.viz_type) {
      case "big_number_total": return "monitoring";
      case "table": return "table_view";
      case "pie": return "donut_small";
      case "treemap_v2": return "grid_view";
      default: return "bar_chart";
    }
  }

  function buildDashboardGrid() {
    const kpiGrid = $("kpiGrid");
    const dashGrid = $("dashboardGrid");
    kpiGrid.innerHTML = "";
    dashGrid.innerHTML = "";
    state.tables = {};
    state.echarts = {};

    const charts = state.meta.charts;
    charts.forEach((spec, idx) => {
      if (spec.section === "kpi" || spec.viz_type === "big_number_total") {
        const card = document.createElement("div");
        card.className = "metric-card";
        card.dataset.chartId = String(spec.id);
        card.innerHTML = `
          <div class="metric-header">
            <span class="metric-label">${escapeHtml(spec.title)}</span>
            <span class="metric-icon-box"><span class="material-symbols-outlined" aria-hidden="true">${chartIcon(spec)}</span></span>
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
        const cols = (spec.columns && spec.columns.length) ? spec.columns : [...(spec.groupby || []), ...((spec.metrics || []).map((m) => m.label))];
        card.innerHTML = `
          <div class="table-header">
            <div>
              <h2>${escapeHtml(spec.title)}</h2>
              <p id="tblSub${spec.id}">${cols.length} kolom dari Superset (chart #${spec.id}).</p>
            </div>
            <div class="table-actions">
              <label class="search-box">
                <span class="material-symbols-outlined" aria-hidden="true">search</span>
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
        return;
      }

      // analytics charts
      const card = document.createElement("article");
      const isTreemap = spec.viz_type === "treemap_v2";
      const isPie = spec.viz_type === "pie";
      card.className = "glass-card chart-card" + (isTreemap ? " span-2" : "");
      card.dataset.chartId = String(spec.id);
      const description = `Source: Superset chart #${spec.id} · ${spec.viz_type}`;
      if (isPie) {
        card.innerHTML = `
          <div class="card-heading">
            <h2>${escapeHtml(spec.title)}</h2>
            <p>${description}</p>
          </div>
          <div class="donut-layout">
            <div class="chart donut-chart" id="chart${spec.id}" data-chart-id="${spec.id}"></div>
            <div class="legend-list" id="legend${spec.id}"></div>
          </div>`;
      } else {
        const heightClass = isTreemap ? "chart-treemap" : (spec.dimension === "tahun" ? "chart-large" : "chart-medium chart-scroll");
        card.innerHTML = `
          <div class="card-heading">
            <h2>${escapeHtml(spec.title)}</h2>
            <p>${description}</p>
          </div>
          <div class="chart ${heightClass}" id="chart${spec.id}" data-chart-id="${spec.id}"></div>`;
      }
      dashGrid.appendChild(card);
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
    state.meta.charts.forEach((spec) => {
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
        footEl.textContent = `Source: Superset chart #${spec.id}`;
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
    if (!chart) chart = echarts.init(el, null, { renderer: "canvas" });
    state.echarts[elId] = chart;
    return chart;
  }

  function makeChart(elId, option) {
    const chart = getChart(elId);
    if (!chart) return;
    chart.setOption(option, true);
    return chart;
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

    const cats = records.map((r) => String(r[dimKey] ?? ""));
    const vals = records.map((r) => cleanNumber(r[metKey]));
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

    const rows = records.map((r, i) => ({ name: String(r[dimKey] ?? ""), value: vals[i] }));

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

    const tree = [];
    const index = {};
    records.forEach((r) => {
      const top = String(r[topKey] ?? "—");
      const child = String(r[childKey] ?? "—");
      const val = cleanNumber(r[metKey]);
      if (!index[top]) {
        index[top] = { name: top, value: 0, children: [] };
        tree.push(index[top]);
      }
      index[top].children.push({ name: child, value: val });
      index[top].value += val;
    });

    makeChart(elId, {
      animationDuration: 500,
      tooltip: {
        backgroundColor: "var(--surface-glass-solid)",
        borderColor: "var(--surface-glass-border)",
        textStyle: { color: "var(--text-primary)", fontSize: 12 },
        formatter: (p) => `<div style="font-weight:700">${escapeHtml(p.name)}</div><div style="margin-top:4px">${fmtCurrency(cleanNumber(p.value))}</div>`,
      },
      series: [{
        type: "treemap",
        roam: false,
        nodeClick: "zoomToNode",
        breadcrumb: { show: true, itemStyle: { color: "var(--accent-primary)", borderRadius: 6 }, textStyle: { color: "#fff", fontSize: 10 } },
        label: { show: true, color: "#fff", fontSize: 11, fontWeight: 600, formatter: (p) => `${p.name}\n${fmtCompactCurrency(p.value)}` },
        upperLabel: { show: true, height: 22, color: "#fff", fontSize: 11, fontWeight: 700 },
        itemStyle: { borderColor: "var(--surface-glass-solid)", borderWidth: 2, gapWidth: 2, borderRadius: 6 },
        levels: [
          { itemStyle: { borderColor: "var(--surface-glass-solid)", borderWidth: 2, gapWidth: 2 } },
          { colorSaturation: [0.25, 0.65], itemStyle: { borderWidth: 1, gapWidth: 1 } },
        ],
        data: tree.map((t, i) => ({ ...t, itemStyle: { color: state.palette[i % state.palette.length] } })),
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

    const data = records.map((r) => ({ name: String(r[dimKey] ?? "—"), value: cleanNumber(r[metKey]) }));
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
    const totalPages = Math.max(1, Math.ceil(rows.length / st.size));
    if (st.page >= totalPages) st.page = totalPages - 1;
    const pageRows = rows.slice(st.page * st.size, st.page * st.size + st.size);

    const header = cols.map((c) => {
      const lower = c.toLowerCase();
      const numeric = lower.includes("jumlah") || lower.includes("harga") || lower.includes("total") || c === "qty" || c === "source_row";
      return `<th class="${numeric ? "num" : ""}">${escapeHtml(String(c))}</th>`;
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
        const numeric = lower.includes("jumlah") || lower.includes("harga") || lower.includes("total") || c === "qty" || c === "source_row";
        return `<td class="${numeric ? "num" : ""}">${escapeHtml(formatValueForColumn(v, c))}</td>`;
      }).join("") + "</tr>";
    }).join("");

    if (wrap) wrap.innerHTML = `<table class="apple-table"><thead><tr>${header}</tr></thead><tbody>${body || '<tr class="tbl-empty"><td>Pencarian tidak menemukan hasil.</td></tr>'}</tbody></table>`;

    const sub = $(`tblSub${id}`);
    if (sub) sub.textContent = `${fmtInt.format(records.length)} baris dari Superset (chart #${id})${st.search ? ` — ${fmtInt.format(rows.length)} hasil pencarian` : ""}.`;

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
  function renderDashboard(errors) {
    renderKpis();
    state.meta.charts.forEach((spec) => {
      if (spec.viz_type === "big_number_total") return;
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
    });
    renderStatusPanel(errors);
    const anyFail = errors.length > 0;
    setSourceStatus(anyFail ? "warn" : "ok", anyFail ? `Sumber tersambung · ${errors.length} chart gagal` : "Sumber terhubung · Superset API");
    $("footerStatus").textContent = anyFail ? `${errors.length} chart bermasalah` : "Semua chart berhasil dimuat";
  }

  async function refreshDashboard(force) {
    const btn = $("refreshDashboard");
    btn.classList.add("spinning");
    btn.disabled = true;
    try {
      const errors = await loadAll(state.activeYear, force);
      renderDashboard(errors);
      if (force) showToast("Data terbaru diambil dari Superset");
    } catch (err) {
      setSourceStatus("err", "Gagal menghubungi Superset API");
      $("footerStatus").textContent = "Gagal menghubungi Superset API";
      renderStatusPanel([err.message]);
    } finally {
      btn.classList.remove("spinning");
      btn.disabled = false;
    }
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
    window.addEventListener("resize", () => {
      Object.values(state.echarts).forEach((ch) => ch.resize());
    });
  }

  async function init() {
    bindEvents();
    try {
      await loadDashboards();
      state.activeDashboardId = state.dashboards[0] ? state.dashboards[0].id : 2;
      await selectDashboard(state.activeDashboardId);
    } catch (err) {
      setSourceStatus("err", "Gagal menghubungi Superset API");
      $("footerStatus").textContent = "Gagal menghubungi Superset API";
      renderStatusPanel([err.message]);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
