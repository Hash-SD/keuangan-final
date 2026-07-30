import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "outputs/synthetic_2027";
await fs.mkdir(outputDir, { recursive: true });

const workbook = Workbook.create();
const rab = workbook.worksheets.add("RAB");
rab.showGridLines = false;

const headers = [
  "Kode",
  "Uraian",
  "C",
  "D",
  "E",
  "F",
  "G",
  "Qty",
  "Satuan",
  "J",
  "Harga Satuan",
  "L",
  "M",
  "N",
  "O",
  "Jumlah Usulan",
];

const items = [
  ["Penguatan IKU Sains Data 2027 IK 6.7", "Kuliah Lapangan Industri 2027 IK 6.7", "524111 - Perjalanan Dinas", [
    ["Transportasi dan akomodasi kunjungan industri nasional IK 6.7", 2, "paket", 36500000],
    ["Registrasi kunjungan pusat data dan industri AI IK 6.7", 1, "paket", 18500000],
    ["Asuransi dan operasional mahasiswa lapangan IK 6.7", 1, "paket", 12500000],
    ["Dokumentasi pembelajaran lapangan IK 6.7", 1, "paket", 6000000],
  ]],
  ["Penguatan IKU Sains Data 2027 IK 4.5", "Workshop Kurikulum dan Silabus Terintegrasi IK 4.5", "521211 - Bahan & Alat", [
    ["Konsumsi peserta workshop kurikulum IK 4.5", 3, "kegiatan", 8750000],
    ["Cetak modul dan bahan ajar berbasis proyek IK 4.5", 1, "paket", 9500000],
    ["Lisensi perangkat kolaborasi kurikulum IK 4.5", 1, "paket", 12000000],
    ["ATK dan perlengkapan kelas desain kurikulum IK 4.5", 1, "paket", 4000000],
  ]],
  ["Penguatan IKU Sains Data 2027 IK 7.3", "Sertifikasi Kompetensi Mahasiswa Internasional IK 7.3", "522151 - Jasa Profesi", [
    ["Honor asesor sertifikasi data analyst IK 7.3", 4, "orang", 11500000],
    ["Biaya ujian sertifikasi internasional IK 7.3", 1, "paket", 32000000],
    ["Pelatihan persiapan sertifikasi IK 7.3", 2, "kelas", 9500000],
    ["Review portofolio mahasiswa IK 7.3", 1, "paket", 7500000],
  ]],
  ["Penguatan IKU Sains Data 2027 IK 4.3", "FGD Industri dan Mitra IK 4.3", "522141 - Sewa Peralatan", [
    ["Sewa ruang dan perangkat hybrid FGD IK 4.3", 2, "hari", 13500000],
    ["Sewa perangkat streaming dan dokumentasi IK 4.3", 1, "paket", 8500000],
    ["Konsumsi mitra dan narasumber FGD IK 4.3", 1, "paket", 9500000],
    ["Penyusunan laporan kemitraan IK 4.3", 1, "paket", 6000000],
  ]],
  ["Penguatan IKU Sains Data 2027 IK 2", "Guest Lecture Series IK 2", "522151 - Jasa Profesi", [
    ["Honor narasumber praktisi data engineering IK 2", 3, "orang", 10000000],
    ["Honor narasumber data governance IK 2", 2, "orang", 8750000],
    ["Produksi materi pembelajaran tamu IK 2", 1, "paket", 7500000],
    ["Operasional kelas tamu hybrid IK 2", 1, "paket", 5000000],
  ]],
  ["Penguatan Operasional Laboratorium Data 2027 IK 6.7", "Operasional Laboratorium Data IK 6.7", "521211 - Bahan & Alat", [
    ["Komponen praktikum sensor dan data capture IK 6.7", 1, "paket", 16000000],
    ["Bahan habis pakai laboratorium data IK 6.7", 2, "paket", 6250000],
    ["Pemeliharaan perangkat praktikum IK 6.7", 1, "paket", 9000000],
    ["Kalibrasi perangkat komputasi kecil IK 6.7", 1, "paket", 5250000],
  ]],
  ["Penguatan Publikasi dan Diseminasi 2027 IK 5", "Publikasi dan Diseminasi Proyek Mahasiswa IK 5", "524111 - Perjalanan Dinas", [
    ["Perjalanan diseminasi kompetisi mahasiswa IK 5", 1, "paket", 18500000],
    ["Registrasi seminar nasional proyek mahasiswa IK 5", 2, "paket", 6500000],
    ["Produksi poster dan materi diseminasi IK 5", 1, "paket", 3750000],
    ["Pendampingan luaran proyek mahasiswa IK 5", 1, "paket", 4500000],
  ]],
];

const rows = [];
const fills = new Map();
rows.push(["RAB IKU Prodi Sains Data 2027 Synthetic Regression Fixture", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]);
rows.push(["Tahun", "2027", "Prodi", "Sains Data", "Catatan", "Synthetic fixture - bukan data faktual", "", "", "", "", "", "", "", "", "", ""]);
rows.push(headers);
let rowIndex = 4;
const parentRows = [];
for (const [nomenklatur, kegiatan, akun, details] of items) {
  rows.push(["", nomenklatur, "", "", "", "", "", "", "", "", "", "", "", "", "", ""]);
  fills.set(rowIndex, "#FFFF00");
  rowIndex++;
  rows.push(["", kegiatan, "", "", "", "", "", "", "", "", "", "", "", "", "", ""]);
  fills.set(rowIndex, "#FF0000");
  rowIndex++;
  const accountRow = rowIndex;
  rows.push([akun.split(" - ")[0], akun, "", "", "", "", "", "", "", "", "", "", "", "", "", null]);
  fills.set(rowIndex, "#92D050");
  rowIndex++;
  const firstDetailRow = rowIndex;
  for (const [desc, qty, satuan, amount] of details) {
    const harga = Math.round(amount / qty);
    rows.push(["", desc, "", "", "", "", "", qty, satuan, "", harga, "", "", "", "", amount]);
    rowIndex++;
  }
  const lastDetailRow = rowIndex - 1;
  parentRows.push([accountRow, firstDetailRow, lastDetailRow]);
}
rows.push(["TOTAL", "Total synthetic RAB 2027", "", "", "", "", "", "", "", "", "", "", "", "", "", null]);
const totalRow = rowIndex;

rab.getRangeByIndexes(0, 0, rows.length, 16).values = rows;
rab.getRange(`A3:P3`).format = { fill: "#D8D8D8", font: { bold: true, color: "#1F2937" }, borders: { preset: "all", style: "thin", color: "#CBD5E1" } };
rab.getRange("A1:P1").merge();
rab.getRange("A1").format = { fill: "#0F4C81", font: { bold: true, color: "#FFFFFF", size: 14 } };
rab.getRange("A2:P2").format = { fill: "#EEF2F7", font: { color: "#334155" } };
for (const [r, color] of fills.entries()) {
  rab.getRange(`A${r}:P${r}`).format = { fill: color, font: { bold: true, color: color === "#FF0000" ? "#FFFFFF" : "#111827" } };
}
for (const [accountRow, firstDetailRow, lastDetailRow] of parentRows) {
  rab.getRange(`P${accountRow}`).formulas = [[`=SUM(P${firstDetailRow}:P${lastDetailRow})`]];
}
rab.getRange(`P${totalRow}`).formulas = [[`=SUM(${parentRows.map(([accountRow]) => `P${accountRow}`).join(",")})`]];
rab.getRange(`H4:H${totalRow}`).format.numberFormat = "#,##0";
rab.getRange(`K4:K${totalRow}`).format.numberFormat = "#,##0";
rab.getRange(`P4:P${totalRow}`).format.numberFormat = "#,##0";
rab.getRange("B:B").format.columnWidth = 58;
rab.getRange("H:H").format.columnWidth = 10;
rab.getRange("I:I").format.columnWidth = 14;
rab.getRange("K:K").format.columnWidth = 16;
rab.getRange("P:P").format.columnWidth = 18;
rab.freezePanes.freezeRows(3);

function addDetailSheet(name, account, detailRows) {
  const ws = workbook.worksheets.add(name);
  ws.showGridLines = false;
  ws.getRange("A1:E1").values = [[`Detail support ${name} - synthetic 2027`, "", "", "", ""]];
  ws.getRange("A1:E1").merge();
  ws.getRange("A1").format = { fill: "#0F4C81", font: { bold: true, color: "#FFFFFF" } };
  ws.getRange("A2:E2").values = [["Uraian Detail", "Qty", "Satuan", "Harga Satuan", "Jumlah Usulan"]];
  ws.getRange("A2:E2").format = { fill: "#E2E8F0", font: { bold: true } };
  const data = detailRows.map(([desc, qty, satuan, amount]) => [desc, qty, satuan, Math.round(amount / qty), amount]);
  ws.getRangeByIndexes(2, 0, data.length, 5).values = data;
  ws.getRange(`A${data.length + 4}:E${data.length + 4}`).values = [["Akun", account, "", "", ""]];
  ws.getRange("A:A").format.columnWidth = 58;
  ws.getRange("D:E").format.numberFormat = "#,##0";
}

addDetailSheet("perjalanan dinas - ok", "524111 - Perjalanan Dinas", [...items[0][3], ...items[6][3]]);
addDetailSheet("belanja bahan", "521211 - Bahan & Alat", [...items[1][3], ...items[5][3]]);
addDetailSheet("jasa profesi - ok", "522151 - Jasa Profesi", [...items[2][3], ...items[4][3]]);

const inspect = await workbook.inspect({
  kind: "sheet,formula,table",
  maxChars: 4000,
  tableMaxRows: 8,
  tableMaxCols: 8,
});
console.log(inspect.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  summary: "formula error scan",
});
console.log(formulaErrors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(`${outputDir}/RAB_2027_SD_RAB_IKU_synthetic.xlsx`);
