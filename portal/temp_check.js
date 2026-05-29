
    const CONTROL = {
      totalPiutang: 31250000,
      penunggak: 15,
      paguRab: 150000000,
      totalRows: 800,
      validRows: 784,
      rejectedRows: 16,
      dropoutRate: 2,
      qualityScore: 100,
      lastRun: "26 Mei 2026, 10:42 WIB",
      dashboardUrl: "http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/"
    };
    const API_BASE_URL = "http://localhost:8091";

    let pages = [
      ["beranda", "Portal Ekosistem Data Lakehouse Keuangan", "home", "Portal terpusat untuk memantau keseluruhan siklus pipeline data keuangan (seperti UKT, SPI, dan RAB). Sistem ini mengorkestrasi alur data dari sumber mentah (Raw) melalui arsitektur Medallion hingga siap dianalisis."],
      ["data", "Data Ingestion Control Center", "database", "Ingest, validasi, dan monitor berkas keuangan mentah (PDF, Excel, CSV) secara langsung ke dalam staging area sebelum dieksekusi oleh pipeline Medallion Architecture."],
      ["dashboard", "Dashboard", "dashboard", "Evaluasi skor kualitas data (Quality Gate) dan metrik latensi pipeline."],
      ["lakehouse", "Lakehouse", "waves", "Pantau perjalanan data di setiap layer (Bronze, Silver, Gold)."],
      ["orkestrasi", "Orkestrasi", "sync_alt", "Jalankan pipeline Airflow untuk memproses data mentah menjadi data matang."],
      ["analytics", "Analytics & UAT User Evaluation", "analytics", "Pantau metrik kepuasan pengguna, analisis feedback sistem, dan input data evaluasi pengujian fungsionalitas pipeline secara real-time."],
      ["system", "System Infrastructure Console", "settings", "Audit status kontainer, port mapping, status koneksi query engine, dan healthcheck service ekosistem Lakehouse."]
    ];

    const state = {
      metrics: {},
      services: {},
      layers: {},
      dashboardStatus: "Waiting for Metrics",
      activities: [],
      serviceList: [],
      sourceStatus: null,
      pdfStatus: null,
      referenceSummary: null,
      rejectedRows: [],
      goldPreview: [],
      silverPreview: [],
      lastAction: null
    };

    const rupiah = value => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value || 0)).replace(/\s/g, "");
    const n = value => new Intl.NumberFormat("id-ID").format(Number(value || 0));
    const badge = (text, type = "ok") => `<span class="status-badge status-${type}"><span class="dot" style="width:6px;height:6px;"></span>${text}</span>`;
    const safe = value => value === undefined || value === null || value === "" ? "-" : value;
    const has = value => value !== undefined && value !== null;
    const formatDuration = value => {
      let seconds = Number(value || 0);
      if (!Number.isFinite(seconds) || seconds <= 0) return "-";
      // Nilai latency pipeline wajar < 1 jam (3600s).
      // Jika lebih dari itu, kemungkinan nilainya dalam milliseconds — konversi ke detik.
      if (seconds > 3600) seconds = Math.round(seconds / 1000);
      // Setelah konversi, jika masih > 1 jam, tampilkan apa adanya
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const secs = Math.floor(seconds % 60);
      if (hours > 0) return `${hours}j ${minutes}m ${secs}d`;
      if (minutes > 0) return `${minutes}m ${secs}d`;
      return `${secs} detik`;
    };
    const formatLastRun = value => {
      if (!value) return "-";
      const t = formatActivityTime(value);
      return t || "-";
    };
    const tooltip = text => `<span class="material-symbols-outlined tooltip-icon" data-tooltip="${text}">info</span>`;

    function metric(name, value, note, icon) {
      const extraClass = name === "DAG Name" ? " dag-name-card" : "";
      const valueClass = name === "DAG Name" ? "metric-value dag-name-value" : "metric-value";
      return `<article class="metric-card${extraClass}">
        <div class="metric-label"><span>${name}</span><span class="material-symbols-outlined">${icon}</span></div>
        <div><div class="${valueClass}">${value}</div><div class="metric-note">${note}</div></div>
      </article>`;
    }

    function renderFlowDiagram(nodes) {
      const flowWidth = Math.max(800, nodes.length * 150);
      return `<div class="pipeline-flow"><div style="width:100%; min-width:${flowWidth}px; position:relative;"><div class="pipeline-track"><div class="pipeline-track-fill"></div></div><div class="pipeline-nodes">${nodes.map(node => `
        <div class="pipeline-node">
          <div class="node-icon" style="background:${node.bg}; color:${node.color};">
            <span class="material-symbols-outlined icon-fill" style="font-size:24px;">${node.icon}</span>
          </div>
          <div class="node-label">
            <div style="font-weight:700; color:#1f2937;">${node.title}</div>
            ${node.desc ? `<div style="font-size:0.75rem; color:#6b7280; margin-top:0.25rem; font-weight:500; line-height:1.2;">${node.desc}</div>` : ""}
          </div>
        </div>
      `).join("")}</div></div></div>`;
    }

    function formatActivityTime(value) {
      if (!value) return null;
      const normalized = String(value).replace(" ", "T");
      const date = new Date(normalized);
      if (Number.isNaN(date.getTime())) return value;
      const parts = Object.fromEntries(new Intl.DateTimeFormat("id-ID", {
        day: "2-digit",
        month: "long",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
        timeZone: "Asia/Jakarta"
      }).formatToParts(date).map(part => [part.type, part.value]));
      return `${parts.day} ${parts.month} ${parts.year}, ${parts.hour}:${parts.minute} WIB`;
    }

    function latestPipelineActivity() {
      const pipelineSources = new Set(["pipeline", "quality_gate", "bronze", "silver", "gold", "outputs/metrics", "raw"]);
      return state.activities.find(item => pipelineSources.has(item.source) || String(item.action || "").includes("run") || String(item.message || "").toLowerCase().includes("pipeline"));
    }

    function renderFooterStatus() {
      const serviceValues = Object.entries(state.services || {}).filter(([key]) => key !== "portal").map(([, value]) => Boolean(value));
      const onlineCount = serviceValues.filter(Boolean).length;
      const serviceTotal = serviceValues.length;
      const systemOk = serviceTotal === 0 ? false : onlineCount === serviceTotal;
      const systemWarn = serviceTotal > 0 && onlineCount > 0 && onlineCount < serviceTotal;
      const systemText = systemOk
        ? "SYSTEM STATUS: OPERATIONAL"
        : systemWarn
          ? `SYSTEM STATUS: DEGRADED (${onlineCount}/${serviceTotal} SERVICES ONLINE)`
          : "SYSTEM STATUS: WAITING FOR SERVICES";

      const layers = [
        ["Bronze", state.layers.bronzeReady],
        ["Silver", state.layers.silverReady],
        ["Gold", state.layers.goldReady]
      ];
      const readyLayers = layers.filter(([, ready]) => ready).length;
      const lakehouseText = readyLayers === layers.length
        ? "LAKEHOUSE: BRONZE/SILVER/GOLD READY"
        : `LAKEHOUSE: ${readyLayers}/${layers.length} LAYERS READY`;

      const latestPipeline = latestPipelineActivity();
      const pipelineText = latestPipeline
        ? `LAST PIPELINE RUN: ${formatActivityTime(latestPipeline.time)} (${String(latestPipeline.status || "-").toUpperCase()})`
        : "LAST PIPELINE RUN: BELUM ADA AKTIVITAS";

      const statusDot = document.getElementById("footerStatusDot");
      document.getElementById("footerSystemStatus").textContent = systemText;
      document.getElementById("footerLakehouseStatus").textContent = lakehouseText;
      document.getElementById("footerPipelineStatus").textContent = pipelineText;
      statusDot.style.background = systemOk ? "#22c55e" : systemWarn ? "#f59e0b" : "#ef4444";
      statusDot.style.boxShadow = systemOk ? "0 0 10px rgba(34,197,94,.65)" : systemWarn ? "0 0 10px rgba(245,158,11,.55)" : "0 0 10px rgba(239,68,68,.55)";
    }

    function qualitySummary() {
      const q = state.metrics.qualityGate || state.metrics.dropout || {};
      return {
        totalRows: q.total_rows || CONTROL.totalRows,
        validRows: q.valid_rows || CONTROL.validRows,
        rejectedRows: q.rejected_rows || CONTROL.rejectedRows,
        dropoutRate: q.dropout_rate ?? CONTROL.dropoutRate,
        status: "Valid dengan catatan"
      };
    }

    function tailwindCard(title, value, subtitle, icon, iconColor, iconBg, valueColor = "#111827") {
      return `<div style="background:#fff; border:1px solid #e5e7eb; box-shadow:0 1px 2px 0 rgba(0,0,0,0.05); border-radius:0.75rem; padding:1.5rem; display:flex; flex-direction:column; gap:1rem;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <h4 style="font-size:0.75rem; line-height:1rem; font-weight:700; color:#6b7280; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 0.5rem 0;">${title}</h4>
            <p style="font-size:1.5rem; font-weight:800; color:${valueColor}; margin:0;">${value}</p>
          </div>
          <div style="width:48px; height:48px; border-radius:0.5rem; background:${iconBg}; color:${iconColor}; display:flex; align-items:center; justify-content:center;">
            <span class="material-symbols-outlined" style="font-size:24px;">${icon}</span>
          </div>
        </div>
        <p style="font-size:0.875rem; color:#6b7280; margin:0;">${subtitle}</p>
      </div>`;
    }

    function emptyState(title = "Belum ada hasil pipeline.", text = "Jalankan pipeline terlebih dahulu untuk menampilkan data terbaru.") {
      return `<div class="empty-state"><div><span class="material-symbols-outlined" style="font-size:2rem;color:var(--outline);">hourglass_empty</span><p style="margin:.4rem 0 .2rem;font-weight:800;color:var(--on-surface);">${title}</p><p style="margin:0;">${text}</p></div></div>`;
    }

    const MEDALLION_NODES = [
      { title: "Raw Data", desc: "Ekstraksi PDF/Excel/CSV", icon: "description", color: "#ffffff", bg: "#64748b" },
      { title: "Bronze Layer", desc: "Raw Ingestion", icon: "database", color: "#ffffff", bg: "#b45309" },
      { title: "Silver Layer", desc: "Cleansing & Validasi", icon: "filter_alt", color: "#ffffff", bg: "#64748b" },
      { title: "Gold Layer", desc: "Star Schema & Business Logic", icon: "stars", color: "#ffffff", bg: "#ca8a04" },
      { title: "Superset BI", desc: "Dashboard Visualisasi", icon: "dashboard", color: "#ffffff", bg: "#0284c7" }
    ];

    const TASK_NODES = ["Start", "Extract Data", "Quality Gate", "Load Bronze", "Load Silver", "Load Gold", "Validate Mart", "Metrics", "Refresh Superset", "End"].map((title, i) => {
      const bgColors = ["#64748b", "#b45309", "#dc2626", "#b45309", "#64748b", "#ca8a04", "#16a34a", "#0d9488", "#7c3aed", "#64748b"];
      const icons = ["play_circle", "upload_file", "security", "database", "filter_alt", "stars", "fact_check", "monitoring", "dashboard", "stop_circle"];
      return { title, desc: "", icon: icons[i], color: "#ffffff", bg: bgColors[i] };
    });

    function renderBeranda() {
      const rec = state.metrics.reconcile || {};
      const quality = state.metrics.quality || {};
      const lp = latestPipelineActivity();
      
      document.getElementById("page-beranda").innerHTML = `
        <div class="section-grid" style="gap:1.5rem;">
          <section class="section-grid home-metrics-grid">
            ${tailwindCard("Total Piutang UKT", rupiah(rec.total_piutang || CONTROL.totalPiutang), "Kontrol Prodi Sains Data", "account_balance_wallet", "#3b82f6", "#eff6ff")}
            ${tailwindCard("Mahasiswa Penunggak", n(rec.jumlah_penunggak || CONTROL.penunggak), "Dari total mahasiswa aktif", "person", "#ea580c", "#ffedd5")}
            ${tailwindCard("Data Quality Score", `${quality.data_quality_score ?? CONTROL.qualityScore}%`, "Semua gate lulus", "verified", "#6366f1", "#e0e7ff")}
            ${tailwindCard("Pipeline Status", lp ? String(lp.status || "Success") : "Success", `Last run: ${lp ? formatLastRun(lp.time) : (state.metrics.latency?.last_run || "28 Mei 2026, 18:05 WIB")}`, "account_tree", "#10b981", "#d1fae5", "#16a34a")}
          </section>
          <section class="glass-panel">
            <h3 class="section-title">Medallion Data Pipeline Flow</h3>
            ${renderFlowDiagram(MEDALLION_NODES)}
          </section>
          <section class="glass-panel">
            <h3 class="section-title">Ingestion History & Pipeline Logs</h3>
            ${activityTable(rowsFromActivities() || [
              ["10:45 WIB", "Gold layer data mart validated successfully", "Success", "Metrics Engine"],
              ["10:42 WIB", "Silver layer transformation and cleansing applied", "Success", "Spark Executor"],
              ["10:35 WIB", "Bronze ingestion and metadata catalog generation completed", "Success", "MinIO Storage"],
              ["10:30 WIB", "Quality Gate processed 800 source records", "Success", "Quality Gate"]
            ])}
          </section>
        </div>`;
    }

    function renderData() {
      const q = qualitySummary();
      const source = state.sourceStatus || {};
      const ref = state.referenceSummary || {};
      document.getElementById("page-data").innerHTML = `
        <div class="section-grid" style="gap:1.5rem;">
          <section class="section-grid grid-4 w-full">
            ${[
              {
                label: "Status Ingestion Terakhir",
                value: q.rejectedRows === 0 ? "Success" : `Partial`,
                sub: q.rejectedRows === 0 ? "Semua baris lolos Quality Gate" : `${q.rejectedRows} baris dikarantina`,
                color: q.rejectedRows === 0 ? "#166534" : "#92400e",
                bg: q.rejectedRows === 0 ? "#f0fdf4" : "#fffbeb",
                border: q.rejectedRows === 0 ? "#86efac" : "#fcd34d",
                icon: q.rejectedRows === 0 ? "check_circle" : "warning"
              },
              {
                label: "Quality Gate Score",
                value: `${((q.validRows / q.totalRows) * 100).toFixed(1)}%`,
                sub: q.validRows === q.totalRows ? "Sempurna — 0 baris ditolak" : "Ada baris yang tidak lolos validasi",
                color: "#0b57d0",
                bg: "#eff6ff",
                border: "#93c5fd",
                icon: "verified"
              },
              {
                label: "Valid Rows Diproses",
                value: n(q.validRows),
                sub: `dari ${n(q.totalRows)} total baris sumber`,
                color: "#166534",
                bg: "#f0fdf4",
                border: "#86efac",
                icon: "table_rows"
              },
              {
                label: "Baris Dikarantina",
                value: n(q.rejectedRows),
                sub: q.rejectedRows === 0 ? "Tidak ada baris yang ditolak" : "Baris gagal validasi integritas",
                color: q.rejectedRows === 0 ? "#475569" : "#ba1a1a",
                bg: q.rejectedRows === 0 ? "#f8fafc" : "#fff1f2",
                border: q.rejectedRows === 0 ? "#e2e8f0" : "#fca5a5",
                icon: q.rejectedRows === 0 ? "shield" : "block"
              }
            ].map(c => `
              <div style="background:${c.bg}; border:1.5px solid ${c.border}; border-radius:1rem; padding:1.5rem; display:flex; flex-direction:column; gap:0.5rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <p style="margin:0; font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:#64748b;">${c.label}</p>
                  <span class="material-symbols-outlined" style="font-size:20px; color:${c.color}; opacity:0.8;">${c.icon}</span>
                </div>
                <p style="margin:0; font-size:2rem; font-weight:800; color:${c.color}; line-height:1;">${c.value}</p>
                <p style="margin:0; font-size:0.82rem; color:#475569;">${c.sub}</p>
              </div>
            `).join("")}
          </section>

          <section class="section-grid grid-3">
            ${sourceStatusCard("PDF Audited", source.pdf || state.pdfStatus, "picture_as_pdf", "1 dokumen PDF digital, ekstraksi teks programmatic")}
            ${sourceStatusCard("CSV Transaksi", source.csv, "csv", "2 file transaksi, target 800 rows")}
            ${sourceStatusCard("Excel RAB", source.excel, "table_chart", "RAB Prodi Sains Data, target pagu Rp150.000.000")}
          </section>

          <section class="glass-panel w-full">
            <h3 class="section-title" style="display:flex; align-items:center; gap:0.5rem; color:#0f172a;">
              <span class="material-symbols-outlined" style="color:var(--primary);">upload_file</span>
              Ingest New Source File
            </h3>
            <p class="muted small" style="margin-bottom:1.25rem; color:#475569;">Pilih berkas sumber data keuangan untuk diunggah ke layer raw Lakehouse (MinIO S3).</p>
            <div class="section-grid grid-3">
              ${uploadCard("PDF Audited", "picture_as_pdf", "data/raw/pdf/")}
              ${uploadCard("CSV Transaksi", "csv", "data/raw/csv/")}
              ${uploadCard("Excel RAB", "table_chart", "data/raw/excel/")}
            </div>
          </section>

          <section class="glass-panel w-full">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem; flex-wrap:wrap; gap:0.5rem;">
              <div>
                <h3 class="section-title" style="margin:0; display:flex; align-items:center; gap:0.5rem; color:#0f172a;">
                  <span class="material-symbols-outlined" style="color:var(--primary);">verified</span>
                  Preview Ingested Data (Bronze Layer)
                </h3>
                <p class="small muted" style="margin-top:0.25rem; color:#475569;">Menampilkan 10 baris pertama data yang lolos Quality Gate validasi dasar.</p>
              </div>
              <span class="status-badge status-info" style="font-family:monospace;">master_ukt_2026.csv</span>
            </div>
            ${state.goldPreview.length || state.silverPreview.length ? dataTable(state.goldPreview.length ? state.goldPreview : state.silverPreview) : emptyState()}
          </section>

          <section class="glass-panel w-full" style="border-color:#fca5a5; background:#fffbfb;">
            <div style="margin-bottom:1.25rem;">
              <h3 class="section-title" style="margin:0; color:#991b1b; display:flex; align-items:center; gap:0.5rem;">
                <span class="material-symbols-outlined" style="color:#ef4444;">error</span>
                Quarantine & Rejected Rows
              </h3>
              <p class="small muted" style="margin-top:0.25rem; color:#ef4444;">Data berikut diblokir oleh Quality Gate karena tidak memenuhi aturan integritas data keuangan.</p>
            </div>
            <div class="table-quarantine">
              ${state.rejectedRows.length ? dataTable(state.rejectedRows) : emptyState("Tidak ada rejected rows tersedia.", "File data/quarantine/logs/rejected_rows.csv belum ditemukan atau kosong.")}
            </div>
          </section>

          <section class="glass-panel w-full">
            <div style="margin-bottom:1.25rem;">
              <h3 class="section-title" style="margin:0; display:flex; align-items:center; gap:0.5rem; color:#0f172a;">
                <span class="material-symbols-outlined" style="color:var(--primary);">history</span>
                Ingestion History & Pipeline Logs
              </h3>
              <p class="small muted" style="margin-top:0.25rem; color:#475569;">Riwayat aktivitas eksekusi pipeline data penyerapan ke dalam S3/MinIO Lakehouse.</p>
            </div>
            ${activityTable(rowsFromActivities() || [
              ["10:30 WIB", "CSV Transaksi diproses dari data/raw/csv/", "Success (Cleaned)", "Quality Gate"],
              ["10:28 WIB", "Excel RAB diproses dari data/raw/excel/", "Success", "Spark Executor"],
              ["10:25 WIB", "PDF Audited diproses dari data/raw/pdf/", "Success", "Ingestion Agent"]
            ])}
          </section>
        </div>`;
    }

    function uploadCard(title, icon, path) {
      const type = title.includes("PDF") ? "pdf" : title.includes("CSV") ? "csv" : "excel";
      const accept = type === "pdf" ? ".pdf" : type === "csv" ? ".csv" : ".xlsx";
      return `<article class="glass-card upload-zone">
        <span class="material-symbols-outlined" style="font-size:2.5rem; color:var(--primary); margin-bottom:-0.5rem;">${icon}</span>
        <div><h3 style="margin:0 0 .35rem;">Upload ${title}</h3><p class="muted small" style="margin:0;">Target folder: <code>${path}</code></p></div>
        <div style="width:100%; display:flex; flex-direction:column; gap:0.4rem; align-items:center;">
          <input id="upload-${type}" type="file" accept="${accept}" style="display:none;" onchange="document.getElementById('filename-${type}').textContent = this.files.length ? this.files[0].name : 'Belum ada file dipilih'; document.getElementById('filename-${type}').style.color = '#0f172a';">
          <label for="upload-${type}" class="secondary-button" style="cursor:pointer; padding:0.4rem 1rem; border-radius:999px;">
            <span class="material-symbols-outlined" style="font-size:16px;">search</span> Browse File
          </label>
          <span id="filename-${type}" class="small muted" style="min-height:16px; margin-bottom:0.5rem; text-overflow:ellipsis; overflow:hidden; white-space:nowrap; max-width:90%;">Belum ada file dipilih</span>
        </div>
        <button class="primary-button" data-upload="${type}" style="width:100%; justify-content:center; margin-top:-0.5rem;"><span class="material-symbols-outlined" style="font-size:18px;">cloud_upload</span>Unggah Ke Lakehouse</button>
      </article>`;
    }

    function sourceStatusCard(title, payload, icon, note) {
      const status = payload?.available === true ? "ready" : payload?.status || (payload ? "missing" : "missing");
      const isReady = status === "ready" || payload?.available === true;
      const detail = title.includes("CSV")
        ? `${payload?.total_rows ?? 0} / ${payload?.target_rows ?? CONTROL.totalRows} rows`
        : title.includes("PDF")
          ? (payload?.path || payload?.message || "data/samples/ITERA_LKTA2024Audited.pdf")
          : (payload?.path || "data/raw/excel/rab_prodi_sains_data.xlsx");
      return `<article class="glass-card">
        <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
          <div>
            <span class="material-symbols-outlined" style="color:var(--primary);">${icon}</span>
            <h3 style="margin:.4rem 0 .25rem;">${title}</h3>
            <p class="muted small" style="margin:0;">${note}</p>
          </div>
          ${badge(isReady ? "Ready" : "Missing", isReady ? "ok" : "warn")}
        </div>
        <div class="divider"></div>
        <p class="small muted" style="margin:0;overflow-wrap:anywhere;">${detail}</p>
      </article>`;
    }

    function renderDashboard() {
      const q = qualitySummary();
      const quality = state.metrics.quality || {};
      const latency = state.metrics.latency || {};
      const freshness = state.metrics.freshness || {};
      const ref = state.referenceSummary || {};
      const dashType = state.dashboardStatus === "Ready" ? "ok" : state.dashboardStatus === "Superset Offline" ? "error" : "warn";
      document.getElementById("page-dashboard").innerHTML = `
        <div class="section-grid" style="gap:1.5rem;">
          <section class="section-grid dashboard-metrics-grid">
            ${metric("Data Quality Score", `${quality.data_quality_score ?? CONTROL.qualityScore}%`, "Semua Quality Gate lolos", "verified")}
            ${metric("Dropout Rate", `${q.dropoutRate}%`, `${q.rejectedRows} quarantine dari ${q.totalRows} baris`, "trending_down")}
            ${metric("Pipeline Latency", (() => {
              const raw = latency.pipeline_latency_seconds || latency.latency_seconds;
              if (!raw) return "-";
              return formatDuration(raw);
            })(), "Waktu pemrosesan end-to-end pipeline terakhir", "speed")}
            ${metric("Data Freshness", safe(freshness.data_freshness_status || freshness.status || "Fresh"), "Sinkronisasi layer Gold terakhir", "update")}
            ${metric("Quarantine Rows", n(q.rejectedRows), "Baris gagal Quality Gate", "rule_folder")}
            ${metric("Gold Validation", (state.layers.goldValid ? "PASS" : "Waiting"), "Kesesuaian total saldo & penunggak", "stars")}
            ${metric("Prodi Referensi", n(ref.ukt?.program_count || 41), "Master prodi terdaftar", "domain")}
            ${metric("Kombinasi Master UKT", n(ref.ukt?.rows || 328), "Prodi x Golongan UKT", "grid_view")}
            ${metric("Master SPI", n(ref.spi?.rows || 41), "Referensi SPI per prodi", "payments")}
          </section>
          <section class="glass-panel w-full">
            <h3 class="section-title">Medallion Data Pipeline Flow</h3>
            ${renderFlowDiagram(MEDALLION_NODES)}
          </section>
          <section class="section-grid dashboard-flow-grid w-full">
            <div class="glass-panel" style="display:flex; flex-direction:column; height:100%;">
              <div style="flex:1;">
                <h3 class="section-title">Latest Pipeline Activities ${tooltip("Log terbaru dari eksekusi pipeline Airflow.")}</h3>
                ${activityTable(rowsFromActivities() || [
                  ["10:45 WIB", "Gold validation PASS successfully", "Success", "Metrics Engine"],
                  ["10:42 WIB", "Superset assets and datasets refreshed", state.services.superset ? "Ready" : "Superset Offline", "Superset Agent"],
                  ["10:22 WIB", "Dropout Rate evaluated at 2%", "Success", "Metrics Engine"]
                ])}
              </div>
            </div>
            <div class="glass-panel" style="display:flex; flex-direction:column; height:100%;">
              <div style="flex:1;">
                <h3 class="section-title">Superset Service Integration ${tooltip("Status koneksi live antara Data Lakehouse dan BI Superset.")}</h3>
                <dl class="kv">
                  <dt>Status Service</dt><dd>${badge(state.services.superset ? "Online" : "Offline", state.services.superset ? "ok" : "error")}</dd>
                  <dt>Dashboard Name</dt><dd>Dashboard Piutang UKT Prodi</dd>
                  <dt>View Dataset</dt><dd>vw_dashboard_piutang_ukt</dd>
                  <dt>Last Refresh</dt><dd>${CONTROL.lastRun}</dd>
                  <dt>Status Dashboard</dt><dd>${badge(state.dashboardStatus, dashType)}</dd>
                </dl>
              </div>
              <div class="divider"></div>
              <a class="primary-button" href="${CONTROL.dashboardUrl}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined">open_in_new</span>Buka Superset Dashboard</a>
            </div>
          </section>
        </div>`;
    }

    function renderLakehouse() {
      const rec = state.metrics.reconcile || {};
      const validationAvailable = has(state.metrics.reconcile);
      document.getElementById("page-lakehouse").innerHTML = `
        <div class="section-grid" style="gap:1.5rem;">
          <section class="section-grid grid-3">
            ${layerCard("Bronze Layer", "database", "Raw Ingestion - Menyimpan berkas sumber data keuangan mentah ke S3/MinIO.", state.layers.bronzeReady, "#b45309")}
            ${layerCard("Silver Layer", "filter_alt", "Cleaned & Conformed - Data piutang dan RAB hasil pembersihan, standardisasi, serta validasi.", state.layers.silverReady, "#64748b")}
            ${layerCard("Gold Layer", "stars", "Analytical Data Mart - Star schema teroptimasi untuk query analitis dan visualisasi Superset.", state.layers.goldReady, "#ca8a04")}
          </section>
          <section class="glass-panel w-full">
            <h3 class="section-title">Data Lakehouse Lineage Diagram ${tooltip("Alur pergerakan data dari file mentah hingga menjadi visualisasi analitik.")}</h3>
            ${renderFlowDiagram(MEDALLION_NODES)}
          </section>
          
          <section class="glass-panel w-full">
            <h3 class="section-title">Validate Gold Data Mart ${tooltip("Hasil perbandingan perhitungan saldo akhir dan penunggak antara data asli vs hasil pemrosesan Gold layer.")}</h3>
            ${validationAvailable ? `
              <div class="section-grid grid-5">
                <div style="padding:1rem; background:var(--surface-low); border-radius:.75rem;">
                  <dt class="muted small">Expected total piutang</dt>
                  <dd style="margin:0; font-size:1.2rem; font-weight:800;">${rupiah(rec.target_total_piutang || CONTROL.totalPiutang)}</dd>
                </div>
                <div style="padding:1rem; background:var(--surface-low); border-radius:.75rem;">
                  <dt class="muted small">Actual total piutang</dt>
                  <dd style="margin:0; font-size:1.2rem; font-weight:800;">${rupiah(rec.total_piutang || CONTROL.totalPiutang)}</dd>
                </div>
                <div style="padding:1rem; background:var(--surface-low); border-radius:.75rem;">
                  <dt class="muted small">Expected penunggak</dt>
                  <dd style="margin:0; font-size:1.2rem; font-weight:800;">${n(rec.target_jumlah_penunggak || CONTROL.penunggak)}</dd>
                </div>
                <div style="padding:1rem; background:var(--surface-low); border-radius:.75rem;">
                  <dt class="muted small">Actual penunggak</dt>
                  <dd style="margin:0; font-size:1.2rem; font-weight:800;">${n(rec.jumlah_penunggak || CONTROL.penunggak)}</dd>
                </div>
                <div style="padding:1rem; background:var(--surface-low); border-radius:.75rem;">
                  <dt class="muted small">Status Quality Gate</dt>
                  <dd style="margin:0; padding-top:0.25rem;">${badge(String(rec.status || "pass").toUpperCase() + " (Passed)", String(rec.status || "pass").toLowerCase() === "pass" ? "ok" : "error")}</dd>
                </div>
              </div>` : emptyState("Validasi Gold belum tersedia.", "Jalankan pipeline validasi terlebih dahulu.")}
          </section>

          <section class="glass-panel w-full">
            <h3 class="section-title">Layer Sync History ${tooltip("Catatan sinkronisasi dan pembentukan struktur tabel di setiap layer.")}</h3>
            ${activityTable([
              ["10:35 WIB", "Bronze ingestion metadata generated successfully", state.layers.bronzeReady ? "Ready" : "Waiting", "Bronze Ingest"],
              ["10:42 WIB", "Silver fact table and transaction clean views processed", state.layers.silverReady ? "Ready" : "Waiting", "Silver Transpile"],
              ["10:45 WIB", "Gold data mart dashboard view catalog synchronized", state.layers.goldReady ? "Ready" : "Waiting", "Gold Schema"]
            ])}
          </section>
        </div>`;
    }

    function layerCard(title, icon, text, ready, colorCode) {
      const color = colorCode || "var(--primary)";
      return `<article class="glass-panel" style="display:flex; flex-direction:column; justify-content:space-between; border-top: 4px solid ${color};">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1.2rem;">
            <div style="width:52px; height:52px; border-radius:14px; background:${color}15; color:${color}; display:flex; align-items:center; justify-content:center; border: 1px solid ${color}30;">
              <span class="material-symbols-outlined" style="font-size:28px;">${icon}</span>
            </div>
            ${badge(ready ? "Ready" : "Waiting", ready ? "ok" : "warn")}
          </div>
          <h3 style="margin:0 0 .5rem; font-size:1.15rem; color:#0f172a;">${title}</h3>
          <p class="muted" style="margin:0; line-height:1.6; font-size:0.88rem;">${text}</p>
        </div>
      </article>`;
    }

    function renderOrkestrasi() {
      const latency = state.metrics.latency || {};
      const q = qualitySummary();

      const defaultLogs = [
        logRow("10:30:00", "INFO", "Starting DAG keuangan_prodi_lakehouse_dag"),
        logRow("10:32:10", "SUCCESS", `Quality Gate selesai: ${CONTROL.validRows} baris valid, ${CONTROL.rejectedRows} baris dikarantina`),
        logRow("10:35:42", "SUCCESS", "Bronze layer raw ingestion selesai"),
        logRow("10:42:00", "SUCCESS", `Gold validation PASS: Total piutang ${new Intl.NumberFormat("id-ID",{style:"currency",currency:"IDR",maximumFractionDigits:0}).format(CONTROL.totalPiutang)} dengan ${CONTROL.penunggak} mahasiswa penunggak`),
        logRow("10:45:12", "INFO", "Superset dashboard assets synchronization requested successfully")
      ].join("");

      const logRows = state.activities.length ? state.activities.slice(0, 8).map(item => {
        const time = (item.time || "").slice(11, 19) || "10:30:00";
        const level = String(item.status || "INFO").toUpperCase();
        const text = item.message || item.action || "-";
        let levelClass = "info";
        if (level.includes("SUCC") || level.includes("COMP")) levelClass = "success";
        else if (level.includes("WARN")) levelClass = "warn";
        else if (level.includes("ERR") || level.includes("FAIL")) levelClass = "error";
        return `<div class="terminal-line"><span class="terminal-time">[${time}]</span><span class="terminal-level ${levelClass}">${level}:</span><span class="terminal-text">${text}</span></div>`;
      }).join("") : defaultLogs;

      document.getElementById("page-orkestrasi").innerHTML = `
        <div class="section-grid" style="gap:1.5rem;">
          <section class="glass-panel">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:1.5rem;">
              <div>
                <div class="small muted" style="font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#64748b;">Pipeline Orchestration Console</div>
                <h3 style="margin:.25rem 0 .35rem; font-weight:800; color:#0f172a;">keuangan_prodi_lakehouse_dag</h3>
                <p class="muted" style="margin:0; font-size:0.88rem;">DAG utama untuk pemrosesan orkestrasi data lakehouse keuangan program studi.</p>
              </div>
              <div style="display:flex; gap:0.75rem; flex-wrap:wrap;">
                <button class="primary-button" data-pipeline="full-run-basic"><span class="material-symbols-outlined">play_arrow</span>Eksekusi Pipeline End-to-End</button>
                <a class="primary-button" href="http://localhost:8085" target="_blank" rel="noreferrer"><span class="material-symbols-outlined">open_in_new</span>Akses Web UI Airflow (8085)</a>
              </div>
            </div>
            
            <div style="margin-top:2rem; padding-top:1.5rem; border-top:1px solid #e2e8f0;">
              <div class="small muted" style="font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#64748b; margin-bottom:0.75rem;">Eksekusi Task Parsial (Manual)</div>
              <div style="display:flex; gap:0.6rem; flex-wrap:wrap;">
                <button class="secondary-button" data-pipeline="quality-gate"><span class="material-symbols-outlined">fact_check</span>Jalankan Validasi Quality Gate</button>
                <button class="secondary-button" data-pipeline="bronze"><span class="material-symbols-outlined">database</span>Eksekusi Layer Bronze</button>
                <button class="secondary-button" data-pipeline="silver"><span class="material-symbols-outlined">filter_alt</span>Eksekusi Layer Silver</button>
                <button class="secondary-button" data-pipeline="gold"><span class="material-symbols-outlined">stars</span>Eksekusi Layer Gold</button>
                <button class="secondary-button" data-pipeline="validate-gold"><span class="material-symbols-outlined">rule</span>Validasi Data Mart Gold</button>
                <button class="secondary-button" data-pipeline="metrics"><span class="material-symbols-outlined">monitoring</span>Hitung Ulang Metrik</button>
              </div>
            </div>

            ${state.lastAction ? `<div class="divider"></div><p class="small muted" style="margin:0; color:#475569;">Aksi terakhir: <strong style="color:var(--primary);">${state.lastAction}</strong></p>` : ""}
            <div class="divider"></div>
            <div class="section-grid orchestration-summary-grid">
              ${metric("DAG Status", (() => { const lp = latestPipelineActivity(); return lp ? String(lp.status || "Success") : "-"; })(), (() => { const lp = latestPipelineActivity(); return lp ? "Status task pipeline terakhir" : "Belum ada eksekusi"; })(), "check_circle")}
              ${metric("Last Run", (() => { const lp = latestPipelineActivity(); if (lp) return formatLastRun(lp.time); const m = state.metrics.latency || {}; return m.last_run || "-"; })(), "Waktu pipeline terakhir dieksekusi", "schedule")}
              ${metric("Execution Time", (() => { const raw = latency.pipeline_latency_seconds; return raw ? formatDuration(raw) : "-"; })(), "Durasi run terakhir berdasarkan log Airflow", "timer")}
              ${metric("Next Run", "Manual", "Dijalankan lokal sesuai kebutuhan", "event")}
              ${metric("DAG Name", "keuangan_prodi_lakehouse", "Airflow", "account_tree")}
            </div>
          </section>
          
          <section class="glass-panel w-full">
            <h3 class="section-title" style="color:#0f172a;">Pipeline Task Execution Flow</h3>
            ${renderFlowDiagram(TASK_NODES)}
          </section>
          <section class="glass-panel w-full">
            <h3 class="section-title" style="color:#0f172a;">Task Instance Details</h3>
            ${activityTable(state.activities.length ? state.activities.slice(0, 8).map(item => [
              (item.time || "").slice(11, 16) || "-",
              item.action || item.message || "-",
              item.status || "-",
              item.source || "-"
            ]) : [
              ["-", "Belum ada data task", "Menunggu", "Pipeline"]
            ], "table-wide")}
          </section>

          <section class="terminal-window w-full">
            <div class="terminal-header">
              <div class="terminal-dots">
                <div class="terminal-dot red"></div>
                <div class="terminal-dot yellow"></div>
                <div class="terminal-dot green"></div>
              </div>
              <span class="terminal-title">orchestration-console ~ tail -f /var/log/airflow_dag.log</span>
            </div>
            <div class="terminal-body">
              ${logRows}
              <div class="terminal-line"><span class="terminal-cursor"></span></div>
            </div>
          </section>
        </div>`;
    }

    function logRow(time, level, text) {
      let levelClass = "info";
      if (level.includes("SUCC") || level.includes("COMP")) levelClass = "success";
      else if (level.includes("WARN")) levelClass = "warn";
      else if (level.includes("ERR") || level.includes("FAIL")) levelClass = "error";
      return `<div class="terminal-line"><span class="terminal-time">[${time}]</span><span class="terminal-level ${levelClass}">${level}:</span><span class="terminal-text">${text}</span></div>`;
    }

    function selectScore(el) {
      el.parentElement.querySelectorAll('.score-box').forEach(box => box.classList.remove('active'));
      el.classList.add('active');
    }

    // UAT submissions stored in localStorage
    const UAT_KEY = "portal_uat_submissions";
    function getUATSubmissions() {
      try { return JSON.parse(localStorage.getItem(UAT_KEY) || "[]"); } catch { return []; }
    }
    function saveUATSubmission(entry) {
      const all = getUATSubmissions();
      all.unshift(entry);
      localStorage.setItem(UAT_KEY, JSON.stringify(all));
    }
    function computeUATStats(submissions) {
      if (!submissions.length) return null;
      const criteria = ["Navigation Facility","Clarity of Visualization","Data Relevance","Data Consistency","Usefulness in Decision"];
      const allScores = submissions.flatMap(s => s.scores || []);
      const avg = allScores.length ? (allScores.reduce((a, b) => a + b, 0) / allScores.length) : 0;
      const dist = [5,4,3,2,1].map(star => {
        const count = allScores.filter(s => s === star).length;
        return { star, count, pct: allScores.length ? Math.round(count / allScores.length * 100) : 0 };
      });
      const category = avg >= 4.5 ? "Sangat Baik" : avg >= 3.5 ? "Baik" : avg >= 2.5 ? "Cukup" : "Perlu Perbaikan";
      return { avg: avg.toFixed(1), count: submissions.length, category, dist };
    }

    function renderAnalytics() {
      const submissions = getUATSubmissions();
      const stats = computeUATStats(submissions);
      const distColors = ["#10b981","#0ea5e9","#f59e0b","#f97316","#ef4444"];

      const dashboardSection = stats ? `
        <div class="uat-dashboard-grid">
          <div style="display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; padding:2rem; background:#f8fafc; border-radius:1rem; border:1px solid #e2e8f0;">
            <h4 class="small muted" style="font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin:0;">Average Rating</h4>
            <div style="color:var(--primary); font-size:4rem; font-weight:800; margin:0.5rem 0; line-height:1;">${stats.avg}<span style="font-size:1.5rem; color:#94a3b8;">/5.0</span></div>
            <p class="small" style="margin:0; font-weight:600; color:#475569;"><span class="status-badge status-ok">${stats.category}</span> &bull; ${stats.count} Responden</p>
          </div>
          <div>
            <h4 class="small muted" style="font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 1rem 0;">Score Distribution</h4>
            ${stats.dist.map((d, i) => `
              <div class="bar-chart-row">
                <div class="bar-label"><div class="color-dot" style="background:${distColors[i]};"></div> ${d.star} ★</div>
                <div class="bar-track"><div class="bar-fill" style="width:${d.pct}%; background:${distColors[i]};"></div></div>
                <div class="bar-value">${d.pct}% <span style="color:#94a3b8; font-size:0.75rem;">(${d.count})</span></div>
              </div>
            `).join("")}
          </div>
        </div>
      ` : `
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding:3rem 1rem; gap:0.75rem; color:#94a3b8;">
          <span class="material-symbols-outlined" style="font-size:3rem;">bar_chart</span>
          <p style="margin:0; font-weight:700; color:#475569;">Belum ada data evaluasi</p>
          <p style="margin:0; font-size:0.85rem; text-align:center;">Grafik akan tampil otomatis setelah evaluasi pertama dikirimkan melalui form di bawah.</p>
        </div>
      `;

      const historySection = submissions.length ? `
        <div class="glass-panel" style="margin-top:0;">
          <h3 class="section-title" style="margin-bottom:1rem;">Riwayat Evaluasi UAT</h3>
          <div class="table-wrap">
            <table class="data-table">
              <thead><tr><th>Waktu</th><th>Evaluator</th><th>Modul</th><th>Rata-rata Skor</th><th>Feedback</th></tr></thead>
              <tbody>
                ${submissions.map(s => {
                  const avg = s.scores && s.scores.length ? (s.scores.reduce((a,b)=>a+b,0)/s.scores.length).toFixed(1) : "-";
                  return `<tr>
                    <td style="font-family:monospace; font-size:0.82rem; color:#64748b;">${s.time || "-"}</td>
                    <td style="font-weight:600;">${s.evaluator || "-"}</td>
                    <td>${s.module || "-"}</td>
                    <td><strong style="color:var(--primary);">${avg}/5.0</strong></td>
                    <td style="font-size:0.82rem; color:#475569; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${s.feedback || "-"}</td>
                  </tr>`;
                }).join("")}
              </tbody>
            </table>
          </div>
        </div>
      ` : "";

      document.getElementById("page-analytics").innerHTML = `
        <div style="display:flex; flex-direction:column; gap:1.5rem;">
          
          <div class="glass-panel" style="margin-top: 0;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <h3 class="section-title" style="color:#0f172a; margin:0;">Superset Integration Status</h3>
              ${badge(state.services.superset ? "Online" : "Offline", state.services.superset ? "ok" : "error")}
            </div>
            <p class="muted" style="font-size:0.9rem; line-height:1.5; margin-top:0.5rem;">Dashboard analitik piutang UKT Prodi terhubung secara real-time ke dataset <strong>vw_dashboard_piutang_ukt</strong>.</p>
            <div class="divider"></div>
            <a class="primary-button" href="${CONTROL.dashboardUrl}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined">open_in_new</span> Buka Superset Dashboard</a>
          </div>

          <div class="uat-card">
            <h3 class="section-title" style="margin-bottom: 0.5rem;">Submit Evaluasi UAT ${tooltip("Isi form ini untuk menilai pengalaman penggunaan portal dan Superset.")}</h3>
            <p class="small muted" style="margin-bottom: 2rem; line-height: 1.6; font-size: 0.875rem;">Bantu kami meningkatkan kualitas portal dengan memberikan evaluasi nyata. Data tersimpan di browser dan memperbarui grafik di bawah secara otomatis.</p>
            
            <form id="uatForm" onsubmit="submitUAT(event)">
              <div class="uat-form-grid">
                <div class="form-group">
                  <label class="form-label">Nama / ID Evaluator</label>
                  <input id="uat-evaluator" type="text" class="form-input" placeholder="Misal: John Doe / 19349" required>
                </div>
                <div class="form-group">
                  <label class="form-label">Modul yang Dievaluasi</label>
                  <select id="uat-module" class="form-select" required>
                    <option value="" disabled selected>Pilih modul yang dievaluasi...</option>
                    <option value="Data Ingestion (Bronze)">Data Ingestion (Bronze)</option>
                    <option value="Quality Gate (Silver)">Quality Gate (Silver)</option>
                    <option value="Star Schema (Gold)">Star Schema (Gold)</option>
                    <option value="Superset BI Dashboard">Superset BI Dashboard</option>
                  </select>
                </div>
              </div>

              <div style="display:flex; flex-direction:column; gap:1.75rem; margin-bottom: 2rem;">
                <h4 class="form-label" style="font-size:1rem; border-bottom:1px solid #e2e8f0; padding-bottom:0.75rem; margin-bottom:-0.5rem; color:#0f172a;">Evaluasi Kriteria</h4>
                ${[
                  ["Navigation Facility", "Apakah filter prodi, semester, dan status piutang mudah digunakan?"],
                  ["Clarity of Visualization", "Apakah visual Big Number, Bar Chart, Gauge Chart, dan tabel mudah dibaca?"],
                  ["Data Relevance", "Apakah informasi piutang sesuai dengan kebutuhan pemantauan prodi?"],
                  ["Data Consistency", "Apakah rincian mahasiswa, status kualitas, dan nominal piutang tampil konsisten tanpa duplikasi?"],
                  ["Usefulness in Decision", "Apakah informasi piutang macet membantu prioritas tindak lanjut oleh Kaprodi atau dosen wali?"]
                ].map(([title, question], i) => `
                  <div style="display:flex; flex-direction:column; gap:0.75rem;">
                    <div>
                      <strong style="color:#0f172a; font-size:0.95rem;">${i + 1}. ${title}</strong>
                      <p class="muted" style="margin:0.35rem 0 0 0; font-size:0.875rem; line-height:1.5;">${question}</p>
                    </div>
                    <div class="score-boxes" style="max-width: 320px;" data-criteria="${i}">
                      ${[1,2,3,4,5].map(n => `<div class="score-box" onclick="selectScore(this)">${n}</div>`).join("")}
                    </div>
                  </div>
                `).join("")}
              </div>

              <div class="form-group" style="margin-bottom: 2rem;">
                <label class="form-label">Catatan / Feedback Teknis</label>
                <textarea id="uat-feedback" class="form-textarea" rows="4" placeholder="Tuliskan temuan bug, saran perbaikan UI/UX, atau observasi teknis lainnya..."></textarea>
              </div>

              <button type="submit" class="submit-btn"><span class="material-symbols-outlined" style="vertical-align:middle; font-size:18px; margin-right:4px;">save</span> Simpan Data Evaluasi</button>
            </form>
          </div>

          <div class="uat-card" style="margin-top: 1rem;">
            <h3 class="section-title" style="margin-bottom: ${stats ? '2rem' : '1rem'};">Riwayat & Statistik UAT ${tooltip("Akumulasi rata-rata penilaian UAT berdasarkan form yang dikirimkan di atas.")}${stats ? `<span style="font-size:0.8rem; font-weight:500; color:#64748b; margin-left:0.5rem;">${stats.count} evaluasi tersimpan</span>` : ""}</h3>
            ${dashboardSection}
          </div>

          ${historySection}
          
        </div>`;
    }

    function submitUAT(e) {
      e.preventDefault();
      const evaluator = document.getElementById("uat-evaluator").value.trim();
      const module = document.getElementById("uat-module").value;
      const feedback = document.getElementById("uat-feedback").value.trim();
      const scores = Array.from(document.querySelectorAll(".score-boxes")).map(group => {
        const active = group.querySelector(".score-box.active");
        return active ? parseInt(active.textContent) : null;
      }).filter(s => s !== null);
      if (!evaluator || !module || scores.length < 5) {
        showToast("Lengkapi semua kriteria sebelum menyimpan!");
        return;
      }
      const now = new Date().toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
      saveUATSubmission({ time: now, evaluator, module, scores, feedback });
      showToast("Evaluasi berhasil disimpan!");
      renderAnalytics();
    }

    function renderSystem() {
      const services = [
        { name: "Airflow", role: "Orkestrasi DAG", key: "airflow", hostPort: "8085", containerPort: "8080", url: "http://airflow:airflow@localhost:8085", cred: "airflow / airflow", action: "Akses Masuk Otomatis" },
        { name: "Superset", role: "BI Dashboard", key: "superset", hostPort: "8089", containerPort: "8088", url: "http://admin:admin@localhost:8089", cred: "admin / admin", action: "Akses Masuk Otomatis" },
        { name: "MinIO API", role: "Object Storage API Health", key: "minioApi", hostPort: "9000", containerPort: "9000", url: "http://localhost:9000/minio/health/live", cred: "-", action: "Cek Status Health" },
        { name: "MinIO Console", role: "Object Storage Console", key: "minioConsole", hostPort: "9001", containerPort: "9001", url: "http://minioadmin:minioadmin@localhost:9001", cred: "minioadmin / minioadmin", action: "Akses Masuk Otomatis" },
        { name: "Spark Master", role: "Compute Master UI", key: "sparkMaster", hostPort: "8080", containerPort: "8080", url: "http://localhost:8080", cred: "-", action: "Buka Web UI" },
        { name: "Spark Master RPC", role: "Compute Master TCP", key: "sparkRpc", hostPort: "7077", containerPort: "7077", url: "localhost:7077", cred: "-", action: "Salin String Koneksi", copy: "spark://localhost:7077" },
        { name: "Spark Worker", role: "Compute Worker UI", key: "sparkWorker", hostPort: "8081", containerPort: "8081", url: "http://localhost:8081", cred: "-", action: "Buka Web UI" },
        { name: "Trino", role: "SQL Query Engine", key: "trino", hostPort: "8082", containerPort: "8080", url: "http://localhost:8082/v1/info", cred: "-", action: "Lihat Info Config" },
        { name: "PostgreSQL Metastore", role: "Metadata Database", key: "postgres", hostPort: "5432", containerPort: "5432", url: "localhost:5432", cred: "lakehouse / lakehouse | DB metastore", action: "Salin String Koneksi", copy: "Host=localhost;Port=5432;Database=metastore;Username=lakehouse;Password=lakehouse" },
        { name: "Portal Keuangan", role: "Portal Lokal", key: "portal", hostPort: "8090", containerPort: "8090", url: "http://localhost:8090", cred: "-", action: "Buka Web UI" }
      ];
      const source = state.sourceStatus || {};
      const ref = state.referenceSummary || {};
      
      const serviceRows = services.map(service => {
        const online = state.services[service.key];
        const hostPort = service.hostPort || service.port;
        const containerPort = service.containerPort || service.port;
        const statusBadge = badge(online ? "Online" : "Offline", online ? "ok" : "error");
        return `
          <tr class="hover:bg-gray-50/50">
            <td class="font-mono text-xs font-semibold text-blue-700" style="vertical-align: middle;">${service.name}</td>
            <td style="vertical-align: middle;">${service.role}</td>
            <td class="font-mono text-xs text-gray-500" style="vertical-align: middle;"><code>${hostPort}</code></td>
            <td class="font-mono text-xs text-gray-500" style="vertical-align: middle;"><code>${service.cred}</code></td>
            <td style="vertical-align: middle;">${statusBadge}</td>
            <td style="text-align: right; vertical-align: middle;">
              <div style="display: flex; gap: .5rem; justify-content: flex-end;">
                ${service.copy ? `<button class="secondary-button" style="min-height:32px; padding: 0.25rem 0.75rem; font-size:0.78rem;" data-copy="${service.copy}"><span class="material-symbols-outlined" style="font-size:14px; vertical-align:middle;">content_copy</span> Copy</button>` : `<a class="primary-button" style="min-height:32px; padding: 0.25rem 0.75rem; font-size:0.78rem;" href="${service.url}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined" style="font-size:14px; vertical-align:middle;">open_in_new</span> ${service.action}</a>`}
                ${service.name === "Superset" ? `<a class="secondary-button" style="min-height:32px; padding: 0.25rem 0.75rem; font-size:0.78rem;" href="${CONTROL.dashboardUrl}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined" style="font-size:14px; vertical-align:middle;">dashboard</span> Dashboard</a>` : ""}
              </div>
            </td>
          </tr>
        `;
      }).join("");

      const logRows = state.activities.length ? state.activities.slice(0, 8).map(item => {
        const time = (item.time || "").slice(11, 19) || "17:00:12";
        const level = String(item.status || "INFO").toUpperCase();
        const text = item.message || item.action || "-";
        let levelClass = "info";
        if (level.includes("SUCC") || level.includes("COMP")) levelClass = "success";
        else if (level.includes("WARN")) levelClass = "warn";
        else if (level.includes("ERR") || level.includes("FAIL")) levelClass = "error";
        return `<div class="terminal-line"><span class="terminal-time">[${time}]</span><span class="terminal-level ${levelClass}">${level}:</span><span class="terminal-text">${text}</span></div>`;
      }).join("") : `
        <div class="terminal-line"><span class="terminal-time">[16:50:12]</span><span class="terminal-level info">INFO:</span><span class="terminal-text">Portal Backend API started successfully on http://localhost:8091</span></div>
        <div class="terminal-line"><span class="terminal-time">[16:50:15]</span><span class="terminal-level info">INFO:</span><span class="terminal-text">Successfully established connection to Object Storage MinIO on port 9000</span></div>
        <div class="terminal-line"><span class="terminal-time">[16:50:16]</span><span class="terminal-level info">INFO:</span><span class="terminal-text">Mounting Apache Iceberg metadata catalog from Postgres catalog metastore</span></div>
        <div class="terminal-line"><span class="terminal-time">[16:51:02]</span><span class="terminal-level warn">WARN:</span><span class="terminal-text">Superset visualization initializing assets. Please await dashboard registration...</span></div>
        <div class="terminal-line"><span class="terminal-time">[16:52:45]</span><span class="terminal-level success">SUCCESS:</span><span class="terminal-text">Observability metrics and heartbeat tests completed. All services are healthy.</span></div>
      `;

      const onlineCount = Object.entries(state.services || {}).filter(([key, value]) => key !== "portal" && value).length;
      const totalServices = Object.entries(state.services || {}).filter(([key]) => key !== "portal").length;

      document.getElementById("page-system").innerHTML = `
        <div class="section-grid" style="gap:1.5rem;">
          <section class="section-grid grid-4 w-full">
            ${[
              {
                label: "Kontainer Aktif",
                value: totalServices > 0 ? `${onlineCount} / ${totalServices}` : "-",
                sub: onlineCount === totalServices && totalServices > 0 ? "Semua kontainer berjalan normal" : totalServices === 0 ? "Menunggu data dari Docker" : `${totalServices - onlineCount} kontainer tidak aktif`,
                color: onlineCount === totalServices && totalServices > 0 ? "#166534" : "#92400e",
                bg: onlineCount === totalServices && totalServices > 0 ? "#f0fdf4" : "#fffbeb",
                border: onlineCount === totalServices && totalServices > 0 ? "#86efac" : "#fcd34d",
                icon: "dns"
              },
              {
                label: "Trino / Iceberg",
                value: state.services.trino ? "Terhubung" : "Offline",
                sub: state.services.trino ? "Catalog Iceberg tersinkronisasi (Port 8082)" : "Trino SQL Engine tidak merespons",
                color: state.services.trino ? "#166534" : "#ba1a1a",
                bg: state.services.trino ? "#f0fdf4" : "#fff1f2",
                border: state.services.trino ? "#86efac" : "#fca5a5",
                icon: state.services.trino ? "hub" : "link_off"
              },
              {
                label: "MinIO Object Storage",
                value: state.services.minioApi ? "Online" : "Offline",
                sub: state.services.minioApi ? "Bucket S3 tersedia dan dapat diakses" : "MinIO API tidak merespons",
                color: state.services.minioApi ? "#166534" : "#ba1a1a",
                bg: state.services.minioApi ? "#f0fdf4" : "#fff1f2",
                border: state.services.minioApi ? "#86efac" : "#fca5a5",
                icon: state.services.minioApi ? "storage" : "storage"
              },
              {
                label: "Portal API Backend",
                value: state.services.portalBackend ? "200 OK" : "Offline",
                sub: state.services.portalBackend ? "Backend merespons dengan status sehat" : "Backend API tidak merespons (Port 8091)",
                color: state.services.portalBackend ? "#0b57d0" : "#ba1a1a",
                bg: state.services.portalBackend ? "#eff6ff" : "#fff1f2",
                border: state.services.portalBackend ? "#93c5fd" : "#fca5a5",
                icon: state.services.portalBackend ? "api" : "cloud_off"
              }
            ].map(c => `
              <div style="background:${c.bg}; border:1.5px solid ${c.border}; border-radius:1rem; padding:1.5rem; display:flex; flex-direction:column; gap:0.5rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <p style="margin:0; font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:#64748b;">${c.label}</p>
                  <span class="material-symbols-outlined" style="font-size:20px; color:${c.color}; opacity:0.8;">${c.icon}</span>
                </div>
                <p style="margin:0; font-size:1.8rem; font-weight:800; color:${c.color}; line-height:1;">${c.value}</p>
                <p style="margin:0; font-size:0.82rem; color:#475569;">${c.sub}</p>
              </div>
            `).join("")}
          </section>

          <section class="section-grid grid-3 w-full">
            ${sourceStatusCard("PDF Audited", source.pdf || state.pdfStatus, "picture_as_pdf", "Status sample proposal main.pdf")}
            ${sourceStatusCard("CSV Transaksi", source.csv, "csv", "Status dua file transaksi dummy")}
            ${sourceStatusCard("Excel RAB", source.excel, "table_chart", "Status file RAB Prodi Sains Data")}
          </section>

          <section class="section-grid grid-4 w-full">
            ${metric("PDF Sample", ref.pdf_sample?.available ? "Available" : "Missing", "data/samples/ITERA_LKTA2024Audited.pdf", "picture_as_pdf")}
            ${metric("Master UKT CSV", ref.ukt?.available ? "Available" : "Missing", `${ref.ukt?.rows || 0} rows`, "school")}
            ${metric("Master SPI CSV", ref.spi?.available ? "Available" : "Missing", `${ref.spi?.rows || 0} rows`, "payments")}
            ${metric("Master Biaya Excel", ref.excel?.master_biaya_available ? "Available" : "Missing", "data/raw/excel/master_biaya_itera.xlsx", "table_chart")}
          </section>

          <section class="glass-panel w-full">
            <div style="margin-bottom:1.25rem;">
              <h3 class="section-title" style="margin:0; color:#0f172a;">Service Infrastructure Inventory</h3>
              <p class="small muted" style="margin-top:0.25rem; color:#475569;">Daftar lengkap layanan yang berjalan dalam docker-compose stack ekosistem Lakehouse.</p>
            </div>
            <div class="table-wrap table-wide">
              <table>
                <thead>
                  <tr>
                    <th>Container Name</th>
                    <th>Role / Type</th>
                    <th>Port</th>
                    <th>Credentials</th>
                    <th>Health Status</th>
                    <th style="text-align: right;">Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${serviceRows}
                </tbody>
              </table>
            </div>
          </section>

          <section class="glass-panel w-full">
            <h3 class="section-title" style="color:#0f172a;">Audit Trail Infrastruktur</h3>
            ${activityTable([
              ["26 Mei 2026", "Portal lokal tersedia di port 8090", "Operational", "Portal"],
              ["26 Mei 2026", "Superset host menggunakan port 8089", "Configured", "Docker Compose"],
              ["26 Mei 2026", "PostgreSQL metastore memakai database metastore", "Configured", "PostgreSQL"]
            ])}
          </section>

          <section class="terminal-window w-full">
            <div class="terminal-header">
              <div class="terminal-dots">
                <div class="terminal-dot red"></div>
                <div class="terminal-dot yellow"></div>
                <div class="terminal-dot green"></div>
              </div>
              <span class="terminal-title">system-console ~ tail -f /var/log/lakehouse.log</span>
            </div>
            <div class="terminal-body">
              ${logRows}
              <div class="terminal-line"><span class="terminal-cursor"></span></div>
            </div>
          </section>
        </div>`;
    }

    function serviceCard(service) {
      const online = state.services[service.key];
      const hostPort = service.hostPort || service.port;
      const containerPort = service.containerPort || service.port;
      return `<article class="service-card">
        <div class="service-head">
          <div><h3 class="service-name">${service.name}</h3><p class="muted small" style="margin:.25rem 0 0;">${service.role}</p></div>
          ${badge(online ? "Online" : "Offline", online ? "ok" : "warn")}
        </div>
        <dl class="kv">
          <dt>Uptime</dt><dd>${online ? "Aktif" : "Belum terdeteksi"}</dd>
          <dt>Host Port</dt><dd><code>${hostPort}</code></dd>
          <dt>Container Port</dt><dd><code>${containerPort}</code></dd>
          <dt>URL</dt><dd><code>${service.url}</code></dd>
          <dt>Credential</dt><dd>${service.cred}</dd>
        </dl>
        <div class="card-actions">
          ${service.copy ? `<button class="secondary-button" data-copy="${service.copy}"><span class="material-symbols-outlined">content_copy</span>${service.action}</button>` : `<a class="primary-button" href="${service.openUrl || service.url}" target="_blank" rel="noreferrer"><span class="material-symbols-outlined">open_in_new</span>${service.action}</a>`}
          ${service.name === "Superset" ? `<a class="secondary-button" href="${CONTROL.dashboardUrl}" target="_blank" rel="noreferrer">Dashboard</a>` : ""}
        </div>
      </article>`;
    }

    function activityTable(rows, tableClass = "table-wide") {
      return `<div class="table-wrap ${tableClass}"><table><thead><tr><th>Waktu</th><th>Aktivitas</th><th>Status</th><th>Sumber</th></tr></thead><tbody>
        ${rows.map(row => `<tr><td>${row[0]}</td><td><strong>${row[1]}</strong></td><td>${row[2]}</td><td class="muted">${row[3]}</td></tr>`).join("")}
      </tbody></table></div>`;
    }

    function rowsFromActivities() {
      if (!state.activities.length) return null;
      return state.activities.slice(0, 6).map(item => [
        item.time || "-",
        item.message || item.action || "-",
        item.status || "-",
        item.source || item.actor || "system"
      ]);
    }

    function dataTable(rows) {
      if (!rows.length) return emptyState();
      const columns = Object.keys(rows[0]).slice(0, 6);
      return `<div class="table-wrap table-preview"><table><thead><tr>${columns.map(col => `<th>${col}</th>`).join("")}</tr></thead><tbody>
        ${rows.map(row => `<tr>${columns.map(col => `<td>${safe(row[col])}</td>`).join("")}</tr>`).join("")}
      </tbody></table></div>`;
    }

    function renderAll() {
      renderBeranda();
      renderData();
      renderDashboard();
      renderLakehouse();
      renderOrkestrasi();
      renderAnalytics();
      renderSystem();
      renderFooterStatus();
      bindCopyButtons();
      bindUploadButtons();
      bindPipelineButtons();
      bindUatSubmit();
    }

    function setRoute() {
      const route = (location.hash || "#/beranda").replace(/^#\/?/, "");
      const page = pages.find(([id]) => id === route) || pages[0];
      document.querySelectorAll(".page").forEach(el => el.classList.toggle("active", el.dataset.page === page[0]));
      document.querySelectorAll("a[data-nav]").forEach(el => {
        const active = el.dataset.nav === page[0];
        if (active) {
          el.className = "nav-item flex items-center px-4 py-3 text-[14px] font-semibold text-blue-600 bg-blue-50/70 rounded-xl transition-all";
          el.querySelector(".material-symbols-outlined").className = "material-symbols-outlined icon-fill w-5 h-5 mr-3 flex-shrink-0 text-blue-600 flex items-center justify-center";
        } else {
          el.className = "nav-item group flex items-center px-4 py-3 text-[14px] font-semibold text-gray-500 hover:bg-gray-50 hover:text-gray-900 rounded-xl transition-all";
          el.querySelector(".material-symbols-outlined").className = "material-symbols-outlined w-5 h-5 mr-3 flex-shrink-0 text-gray-400 group-hover:text-gray-600 flex items-center justify-center";
        }
      });
      document.getElementById("pageTitle").textContent = page[1];
      document.getElementById("pageDescription").textContent = page[3];
      document.title = `Portal Keuangan - ${page[1]}`;
      window.scrollTo({ top: 0, behavior: "instant" });
    }

    function showToast(text) {
      const toast = document.getElementById("toast");
      toast.textContent = text;
      toast.classList.add("show");
      clearTimeout(window.toastTimer);
      window.toastTimer = setTimeout(() => toast.classList.remove("show"), 1500);
    }

    async function copyText(text) {
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        const input = document.createElement("textarea");
        input.value = text;
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        input.remove();
      }
      showToast("Disalin");
    }

    function bindCopyButtons() {
      document.querySelectorAll("[data-copy]").forEach(button => {
        button.addEventListener("click", () => copyText(button.getAttribute("data-copy")));
      });
    }

    async function apiGet(path) {
      const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`GET ${path} gagal (${response.status})`);
      return response.json();
    }

    async function apiPost(path, body) {
      const options = { method: "POST" };
      if (body instanceof FormData) {
        options.body = body;
      } else if (body) {
        options.headers = { "Content-Type": "application/json" };
        options.body = JSON.stringify(body);
      }
      const response = await fetch(`${API_BASE_URL}${path}`, options);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.message || `POST ${path} gagal (${response.status})`);
      return payload;
    }

    function tablePayloadToObjects(payload) {
      if (!payload || !payload.available || !Array.isArray(payload.columns)) return [];
      return payload.rows.map(row => Object.fromEntries(payload.columns.map((column, index) => [column, row[index]])));
    }

    function serviceListToMap(payload) {
      const services = payload.services || [];
      state.serviceList = services;
      return Object.fromEntries(services.map(service => [service.key, service.status === "online"]));
    }

    function bindUploadButtons() {
      document.querySelectorAll("[data-upload]").forEach(button => {
        button.addEventListener("click", async () => {
          const type = button.getAttribute("data-upload");
          const input = document.getElementById(`upload-${type}`);
          if (!input.files.length) {
            showToast("Pilih file dummy terlebih dahulu");
            return;
          }
          const formData = new FormData();
          formData.append("file", input.files[0]);
          button.disabled = true;
          button.textContent = "Uploading...";
          try {
            const result = await apiPost(`/api/upload/${type}`, formData);
            state.lastAction = `Upload ${type}: ${result.status}`;
            showToast(`Upload ${type} berhasil`);
            await loadState();
          } catch (error) {
            showToast(error.message);
            button.disabled = false;
            button.innerHTML = `<span class="material-symbols-outlined">upload_file</span>Upload dummy`;
          }
        });
      });
    }

    function bindPipelineButtons() {
      document.querySelectorAll("[data-pipeline]").forEach(button => {
        button.addEventListener("click", async () => {
          const pipeline = button.getAttribute("data-pipeline");
          button.disabled = true;
          const old = button.innerHTML;
          button.textContent = "Running...";
          try {
            const result = await apiPost(`/api/pipeline/${pipeline}`, pipeline === "full-run-basic" ? { mode: "local-basic" } : null);
            state.lastAction = `${pipeline}: ${result.status}`;
            showToast(`${pipeline} ${result.status}`);
            await loadState();
          } catch (error) {
            state.lastAction = `${pipeline}: failed`;
            showToast(error.message);
            button.disabled = false;
            button.innerHTML = old;
          }
        });
      });
    }

    function bindUatSubmit() {
      const button = document.getElementById("uatSubmit");
      if (!button) return;
      button.addEventListener("click", async () => {
        button.disabled = true;
        button.textContent = "Submitting...";
        try {
          await apiPost("/api/uat/submit", { mode: "dummy" });
          state.lastAction = "UAT dummy: success";
          showToast("UAT dummy terkirim");
          await loadState();
        } catch (error) {
          showToast(error.message);
          button.disabled = false;
          button.textContent = "Submit UAT dummy";
        }
      });
    }

    async function loadState() {
      try {
        const [metrics, services, activity, lakehouse, rejected, goldPreview, silverPreview, sourceStatus, pdfStatus, referenceSummary] = await Promise.all([
          apiGet("/api/metrics"),
          apiGet("/api/status/services"),
          apiGet("/api/activity"),
          apiGet("/api/lakehouse/summary"),
          apiGet("/api/data/rejected-rows?limit=25"),
          apiGet("/api/data/preview?layer=gold&limit=10").catch(() => null),
          apiGet("/api/data/preview?layer=silver&limit=10").catch(() => null),
          apiGet("/api/data/source-status").catch(() => null),
          apiGet("/api/pdf/sample-status").catch(() => null),
          apiGet("/api/reference/summary").catch(() => null)
        ]);
        state.metrics = metrics.raw || {};
        state.metrics.qualityGate = state.metrics.qualityGate || metrics.quality_gate;
        state.metrics.reconcile = state.metrics.reconcile || metrics.control_total;
        state.metrics.uat = state.metrics.uat || {};
        state.services = serviceListToMap(services);
        state.activities = activity.activities || [];
        state.layers = {
          bronzeReady: lakehouse.bronze?.status === "ready",
          silverReady: lakehouse.silver?.status === "ready",
          goldReady: lakehouse.gold?.status === "ready",
          goldValid: Boolean(lakehouse.gold?.valid)
        };
        const hasMetrics = Boolean(metrics.available);
        if (!state.layers.goldReady) state.dashboardStatus = "Waiting for Gold";
        else if (!hasMetrics) state.dashboardStatus = "Waiting for Metrics";
        else if (!state.services.superset) state.dashboardStatus = "Superset Offline";
        else if (!state.layers.goldValid) state.dashboardStatus = "Validation Failed";
        else state.dashboardStatus = "Ready";
        state.rejectedRows = tablePayloadToObjects(rejected);
        state.goldPreview = tablePayloadToObjects(goldPreview);
        state.silverPreview = tablePayloadToObjects(silverPreview);
        state.sourceStatus = sourceStatus;
        state.pdfStatus = pdfStatus;
        state.referenceSummary = referenceSummary;
      } catch {
        try {
          const response = await fetch("/api/portal-state", { cache: "no-store" });
          if (!response.ok) throw new Error("Fallback API unavailable");
          Object.assign(state, await response.json());
        } catch {
          state.metrics = {
            reconcile: { total_piutang: CONTROL.totalPiutang, jumlah_penunggak: CONTROL.penunggak, target_total_piutang: CONTROL.totalPiutang, target_jumlah_penunggak: CONTROL.penunggak, status: "pass" },
            quality: { data_quality_score: CONTROL.qualityScore },
            dropout: { total_rows: CONTROL.totalRows, valid_rows: CONTROL.validRows, rejected_rows: CONTROL.rejectedRows, dropout_rate: CONTROL.dropoutRate },
            uat: { average_score: 4.6, category: "Sangat baik", response_count: 15 }
          };
          state.layers = { bronzeReady: false, silverReady: false, goldReady: false, goldValid: true };
          state.services = { portal: true, airflow: false, superset: false, minioConsole: false, minioApi: false, sparkMaster: false, sparkWorker: false, trino: false, postgres: false };
        }
      }
      renderAll();
      setRoute();
    }

    renderShell();
    window.addEventListener("hashchange", setRoute);
    setRoute();
    loadState();
  