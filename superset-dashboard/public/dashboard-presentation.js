(function exposeDashboardPresentation(root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.SILARASPresentation = api;
})(typeof globalThis !== "undefined" ? globalThis : this, () => {
  const COLUMN_LABELS = Object.freeze({
    tahun: "Tahun",
    periode: "Periode",
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
    summarizeReconciliationStatus,
  });
});
