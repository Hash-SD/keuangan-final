const test = require("node:test");
const assert = require("node:assert/strict");

const {
  displayColumnLabel,
  displayTitle,
  formatKpiValue,
  formatReconciliationStatus,
  isPrimaryMetric,
  normalizeDetailRecord,
  summarizeReconciliationStatus,
  toggleCrossFilter,
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
  assert.equal(displayColumnLabel("qty"), "Kuantitas");
});

test("normalizes missing detail quantity and unit price from the total amount", () => {
  const row = normalizeDetailRecord({ qty: null, harga_satuan: null, jumlah: 2520000 });

  assert.equal(row.qty, 1);
  assert.equal(row.harga_satuan, 2520000);
  assert.equal(row.jumlah, 2520000);
});

test("normalizes formatted detail amounts before applying the fallback", () => {
  const row = normalizeDetailRecord({ qty: null, harga_satuan: null, jumlah: "Rp 2.520.000" });

  assert.equal(row.qty, 1);
  assert.equal(row.harga_satuan, 2520000);
  assert.equal(row.jumlah, 2520000);
});

test("uses the total when either detail field is missing", () => {
  for (const input of [
    { qty: 0, harga_satuan: 50, jumlah: 100 },
    { qty: 2, harga_satuan: null, jumlah: 100 },
  ]) {
    const row = normalizeDetailRecord(input);

    assert.equal(row.qty, 1);
    assert.equal(row.harga_satuan, 100);
  }
});

test("calculates a missing total from quantity and formatted unit price", () => {
  const row = normalizeDetailRecord({ qty: 2, harga_satuan: "Rp 1.250.000", jumlah: null });

  assert.equal(row.qty, 2);
  assert.equal(row.harga_satuan, 1250000);
  assert.equal(row.jumlah, 2500000);
});

test("toggles cross-filters immutably and supports multiple values per field", () => {
  const first = toggleCrossFilter([], "iku", "IK 4.5", false);
  const second = toggleCrossFilter(first, "iku", "IK 7.3", true);
  const cleared = toggleCrossFilter(second, "iku", "IK 4.5", true);

  assert.deepEqual(first, [{ col: "iku", op: "IN", val: ["IK 4.5"] }]);
  assert.deepEqual(second, [{ col: "iku", op: "IN", val: ["IK 4.5", "IK 7.3"] }]);
  assert.deepEqual(cleared, [{ col: "iku", op: "IN", val: ["IK 7.3"] }]);
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
