(function exposeDashboardPresentation(root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.SILARASPresentation = api;
})(typeof globalThis !== "undefined" ? globalThis : this, () => {
  const COLUMN_LABELS = Object.freeze({
    tahun: "Tahun",
    prodi: "Prodi",
    iku: "IKU",
    kegiatan: "Kegiatan",
    akun: "Akun",
    kode_akun: "Kode akun",
    nama_akun: "Nama akun",
    uraian_detail: "Uraian detail",
    qty: "Kuantitas",
    harga_satuan: "Harga satuan",
    jumlah: "Jumlah",
    total_anggaran: "Total anggaran",
    jumlah_item: "Jumlah item",
    jumlah_iku: "Jumlah IKU",
    jumlah_kegiatan: "Jumlah kegiatan",
    jumlah_baris: "Jumlah baris",
    source_file: "Sumber data",
    source_system: "Sistem sumber",
    total_detail: "Total detail",
    total_rekap: "Total rekap",
    selisih: "Selisih",
    status: "Status",
    status_rekonsiliasi: "Status rekonsiliasi",
    mapping_status: "Status pemetaan",
    data_quality_flag: "Kualitas data",
    created_at: "Dibuat pada",
    updated_at: "Diperbarui pada",
    id: "ID",
  });

  const TITLE_LABELS = Object.freeze({
    kpi_status_rekonsiliasi: "KPI status rekonsiliasi",
    status_rekonsiliasi: "Status rekonsiliasi",
    anggaran_per_tahun: "Anggaran per tahun",
    anggaran_per_iku: "Anggaran per IKU",
    cluster_kegiatan: "Klaster kegiatan",
    klaster_kegiatan: "Klaster kegiatan",
    komposisi_akun: "Komposisi akun",
    anggaran_per_akun: "Anggaran per akun",
    ringkasan_per_tahun: "Ringkasan per tahun",
    detail_item_biaya: "Detail item biaya",
    validasi_rekap: "Validasi rekap",
  });

  function displayTitle(title) {
    const cleaned = String(title ?? "")
      .replace(/^\s*SILARAS\s*\|\s*/i, "")
      .replace(/\bcluster\s+kegiatan\b/i, "Klaster Kegiatan")
      .trim();
    return TITLE_LABELS[normalizeKey(cleaned)] || cleaned;
  }

  function normalizeKey(value) {
    return String(value ?? "")
      .trim()
      .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
      .replace(/[\s-]+/g, "_")
      .toLowerCase();
  }

  function displayColumnLabel(value) {
    const raw = String(value ?? "").trim();
    if (!raw) return "";
    const key = normalizeKey(raw);
    if (COLUMN_LABELS[key]) return COLUMN_LABELS[key];

    return raw
      .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/\b\w/g, (character) => character.toUpperCase())
      .replace(/\bIku\b/g, "IKU")
      .replace(/\bId\b/g, "ID");
  }

  function isCountColumn(value) {
    const key = normalizeKey(value);
    return key === "qty"
      || /^jumlah_(item|iku|kegiatan|baris|data)$/.test(key)
      || /(^|_)count($|_)/.test(key);
  }

  function numericOrNull(value) {
    if (value === null || value === undefined || (typeof value === "string" && !value.trim())) return null;
    if (typeof value === "number") return Number.isFinite(value) ? value : null;

    let text = String(value).trim().replace(/[^0-9,.\-]/g, "");
    if (!text || ["-", ".", ","].includes(text)) return null;

    if (text.includes(",") && text.includes(".")) {
      const separatorPositions = [...text].reduce((positions, character, index) => {
        if (character === "," || character === ".") positions.push(index);
        return positions;
      }, []);
      const lastPosition = separatorPositions[separatorPositions.length - 1];
      const decimalSeparator = text.length - lastPosition - 1 !== 3 ? text[lastPosition] : null;
      if (decimalSeparator) {
        const thousandsSeparator = decimalSeparator === "," ? "." : ",";
        text = text.split(thousandsSeparator).join("").replace(decimalSeparator, ".");
      } else {
        text = text.replace(/[,.]/g, "");
      }
    } else if (text.includes(",")) {
      const parts = text.split(",");
      text = parts.length > 1 && parts.slice(1).every((part) => part.length === 3)
        ? parts.join("")
        : text.replace(",", ".");
    } else if (text.includes(".")) {
      const parts = text.split(".");
      if (parts.length > 1 && parts.slice(1).every((part) => part.length === 3)) text = parts.join("");
    }

    const number = Number(text);
    return Number.isFinite(number) ? number : null;
  }

  function normalizeDetailRecord(record) {
    const normalized = { ...(record || {}) };
    let amount = numericOrNull(normalized.jumlah);
    let quantity = numericOrNull(normalized.qty);
    let unitPrice = numericOrNull(normalized.harga_satuan);
    const quantityMissing = quantity === null || quantity === 0;
    const unitPriceMissing = unitPrice === null || unitPrice === 0;

    if (amount === null && !quantityMissing && !unitPriceMissing) {
      amount = quantity * unitPrice;
    }
    if (amount !== null && (quantityMissing || unitPriceMissing)) {
      quantity = 1;
      unitPrice = amount;
    } else {
      if (quantityMissing) quantity = 1;
      if (unitPriceMissing && amount !== null) unitPrice = amount / quantity;
    }

    normalized.qty = quantity;
    normalized.harga_satuan = unitPrice;
    if (amount !== null) normalized.jumlah = amount;
    return normalized;
  }

  function filterValue(value) {
    const normalized = String(value ?? "").trim();
    return normalized || null;
  }

  function toggleCrossFilter(filters, column, value, multi = false) {
    const col = String(column ?? "").trim();
    const val = filterValue(value);
    if (!col || val === null) return (filters || []).map((filter) => ({ ...filter, val: [...filter.val] }));

    const current = Array.isArray(filters) ? filters : [];
    const existing = current.find((filter) => filter.col === col);
    if (!multi) {
      if (existing && existing.val.length === 1 && existing.val[0] === val) {
        return current.filter((filter) => filter.col !== col).map((filter) => ({ ...filter, val: [...filter.val] }));
      }
      return [{ col, op: "IN", val: [val] }];
    }

    if (!existing) return [...current.map((filter) => ({ ...filter, val: [...filter.val] })), { col, op: "IN", val: [val] }];
    const values = existing.val.includes(val)
      ? existing.val.filter((item) => item !== val)
      : [...existing.val, val];
    return current
      .filter((filter) => filter.col !== col || values.length > 0)
      .map((filter) => filter.col === col ? { ...filter, val: [...values] } : { ...filter, val: [...filter.val] });
  }

  function isPrimaryMetric(spec) {
    const metric = spec?.metric || {};
    const descriptor = [spec?.title, metric.label, metric.column?.column_name]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return /total\s+anggaran|anggaran\s+total/.test(descriptor);
  }

  function formatReconciliationStatus(value) {
    const key = String(value ?? "").trim().toLowerCase();
    if (key === "ok" || key.includes("valid") || key.includes("pass") || key.includes("terverifikasi")) {
      return { label: "Terverifikasi", tone: "ok" };
    }
    if (key.includes("warn") || key.includes("review") || key.includes("queue")) {
      return { label: "Perlu ditinjau", tone: "warn" };
    }
    if (key.includes("fail") || key.includes("error") || key.includes("invalid")) {
      return { label: "Gagal diverifikasi", tone: "err" };
    }
    return { label: displayColumnLabel(value) || "Belum ada status", tone: "neutral" };
  }

  function summarizeReconciliationStatus(values) {
    const severity = { neutral: 0, ok: 1, warn: 2, err: 3 };
    return (Array.isArray(values) ? values : [values])
      .map(formatReconciliationStatus)
      .reduce((worst, current) => severity[current.tone] > severity[worst.tone] ? current : worst, {
        label: "Belum ada status",
        tone: "neutral",
      });
  }

  function isCountMetric(spec) {
    const metric = spec?.metric || {};
    const descriptor = [spec?.title, metric.label, metric.column?.column_name]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return /\b(jumlah|count|status)\b/.test(descriptor);
  }

  function formatKpiValue(spec, value, formatters) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    const formatter = isCountMetric(spec) || spec?.value_format !== "currency"
      ? formatters.number
      : formatters.currency;
    return formatter(number);
  }

  return Object.freeze({
    displayColumnLabel,
    displayTitle,
    formatKpiValue,
    formatReconciliationStatus,
    isCountColumn,
    isPrimaryMetric,
    normalizeDetailRecord,
    summarizeReconciliationStatus,
    toggleCrossFilter,
  });
});
