const test = require("node:test");
const assert = require("node:assert/strict");

const {
  displayColumnLabel,
  displayTitle,
  formatKpiValue,
  formatReconciliationStatus,
  isPrimaryMetric,
  summarizeReconciliationStatus,
} = require("../superset-dashboard/public/dashboard-presentation.js");

const formatters = {
  currency: (value) => `Rp ${value}`,
  number: (value) => String(value),
};

test("formats count KPI values without a currency prefix", () => {
  const spec = {
    title: "Jumlah Item",
    metric: { label: "jumlah_item" },
    value_format: "currency",
  };

  assert.equal(formatKpiValue(spec, 253, formatters), "253");
});

test("keeps currency formatting for budget KPI values", () => {
  const spec = {
    title: "Total Anggaran",
    metric: { label: "total_anggaran" },
    value_format: "currency",
  };

  assert.equal(formatKpiValue(spec, 517361656, formatters), "Rp 517361656");
});

test("keeps weighted IKU allocation formatted as currency", () => {
  const spec = {
    title: "Total Weighted IKU",
    metric: { label: "jumlah_weighted_iku" },
    value_format: "currency",
  };

  assert.equal(formatKpiValue(spec, 517361656, formatters), "Rp 517361656");
});

test("marks total budget as the primary KPI", () => {
  assert.equal(isPrimaryMetric({ title: "Total Anggaran" }), true);
  assert.equal(isPrimaryMetric({ title: "Jumlah Item", metric: { label: "jumlah_item" } }), false);
});

test("removes the SILARAS prefix from display titles only", () => {
  assert.equal(displayTitle("SILARAS | KPI Status Rekonsiliasi"), "KPI status rekonsiliasi");
  assert.equal(displayTitle("SILARAS | Detail Item Biaya"), "Detail item biaya");
  assert.equal(displayTitle("SILARAS | Cluster Kegiatan"), "Klaster kegiatan");
  assert.equal(displayTitle("SILARAS | Anggaran per Tahun"), "Anggaran per tahun");
  assert.equal(displayTitle("SILARAS SD"), "SILARAS SD");
});

test("converts technical table keys into readable Indonesian labels", () => {
  assert.equal(displayColumnLabel("source_file"), "Sumber data");
  assert.equal(displayColumnLabel("total_detail"), "Total detail");
  assert.equal(displayColumnLabel("jumlah_item"), "Jumlah item");
  assert.equal(displayColumnLabel("uraian_detail"), "Uraian detail");
});

test("humanizes unknown snake-case table keys without leaking underscores", () => {
  assert.equal(displayColumnLabel("review_owner"), "Review Owner");
});

test("turns reconciliation status values into compact user-facing copy", () => {
  assert.deepEqual(formatReconciliationStatus("OK"), { label: "Terverifikasi", tone: "ok" });
  assert.deepEqual(formatReconciliationStatus("WARN"), { label: "Perlu ditinjau", tone: "warn" });
  assert.deepEqual(formatReconciliationStatus("FAILED"), { label: "Gagal diverifikasi", tone: "err" });
});

test("summarizes the most severe reconciliation status across source rows", () => {
  assert.deepEqual(summarizeReconciliationStatus(["OK", "WARN", "FAILED"]), {
    label: "Gagal diverifikasi",
    tone: "err",
  });
  assert.deepEqual(summarizeReconciliationStatus(["OK", "WARN"]), {
    label: "Perlu ditinjau",
    tone: "warn",
  });
});
