const test = require("node:test");
const assert = require("node:assert/strict");

const { buildTreemapData } = require("../superset-dashboard/public/treemap-data.js");

test("keeps the highest-value groups before merging treemap overflow", () => {
  const records = [
    { iku: "IKU kecil", kegiatan: "Kegiatan kecil", total_anggaran: 5 },
    { iku: "IKU utama", kegiatan: "Kegiatan utama", total_anggaran: 100 },
    { iku: "IKU kedua", kegiatan: "Kegiatan kedua", total_anggaran: 80 },
    { iku: "IKU sisa A", kegiatan: "Kegiatan sisa A", total_anggaran: 10 },
    { iku: "IKU sisa B", kegiatan: "Kegiatan sisa B", total_anggaran: 9 },
  ];

  const groups = buildTreemapData(records, {
    topKey: "iku",
    childKey: "kegiatan",
    metricKey: "total_anggaran",
    maxGroups: 2,
    maxChildren: 2,
  });

  assert.deepEqual(groups.map((group) => group.name), ["IKU utama", "IKU kedua", "Lainnya"]);
  assert.equal(groups.at(-1).value, 24);
  assert.equal(groups.at(-1).isRemainder, true);
  assert.ok(groups[0].value > groups.at(-1).value);
});

test("sorts visible treemap groups without replacing them with low-value overflow", () => {
  const records = [
    { iku: "IKU utama", kegiatan: "Kegiatan utama", total_anggaran: 100 },
    { iku: "IKU kedua", kegiatan: "Kegiatan kedua", total_anggaran: 80 },
    { iku: "IKU sisa", kegiatan: "Kegiatan sisa", total_anggaran: 10 },
  ];

  const groups = buildTreemapData(records, {
    topKey: "iku",
    childKey: "kegiatan",
    metricKey: "total_anggaran",
    maxGroups: 2,
    sortOrder: "asc",
  });

  assert.deepEqual(groups.map((group) => group.name), ["IKU kedua", "IKU utama", "Lainnya"]);
  assert.equal(groups.at(-1).value, 10);
});
