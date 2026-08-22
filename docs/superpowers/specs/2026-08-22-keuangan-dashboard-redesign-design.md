# Redesign Dashboard Keuangan SILARAS — Design

## Tujuan

Membuat dashboard `keuangan-superset-dashboard` terasa seperti alat kerja analitik keuangan yang tenang, jelas, dan dapat dipercaya: angka utama mudah dipindai, istilah teknis tidak bocor ke UI, dan tabel detail tetap tersedia tanpa mengambil alih hierarki halaman.

Gambar referensi pengguna diperlakukan sebagai bukti visual. Gambar memperlihatkan build/surface yang masih menampilkan prefix `SILARAS |`, nama kolom snake_case, jumlah item dengan format Rupiah, kartu status satu baris yang terlalu besar, dan treemap dengan blok `IKU lainnya` yang dominan.

## Arah visual

- **Subjek:** dashboard anggaran dan IKU untuk pengguna Program Studi Sains Data.
- **Karakter:** editorial-operasional; sober seperti lembar kendali anggaran, bukan dashboard SaaS generik.
- **Dials:** variance rendah-sedang (3/10), motion rendah (2/10), density tinggi tetapi terstruktur (7/10).
- **Signature:** satu blok Total Anggaran sebagai jangkar visual dengan aksen teal; metrik jumlah dan status menjadi pendukung yang lebih ringkas.
- **Warna:** satu aksen UI teal dan keluarga netral hijau-kebiruan; warna kategori chart tetap dibatasi dan tidak dipakai sebagai dekorasi kartu.
- **Tipografi:** Plus Jakarta Sans tetap menjadi body/display yang sudah tersedia; angka dan kolom numerik memakai tabular figures; label memakai sentence case, bukan all-caps penuh.

## Struktur halaman

```text
Topbar: kembali | identitas SILARAS SD | status sumber | tema | refresh
Hero: judul dashboard + deskripsi singkat + konteks program studi
Filter: dashboard + tahun + konteks filter aktif
KPI: [Total Anggaran utama] [Jumlah Item] [Jumlah IKU] [Jumlah Kegiatan jika tersedia]
Status: strip ringkas status rekonsiliasi, bukan kartu tabel besar satu baris
Analitik: anggaran/tahun + anggaran/IKU → treemap → akun
Detail: ringkasan tahunan → tabel item → validasi/source bila memang relevan
Footer: status sistem + copyright
```

Status teknis yang tidak punya konteks baris tidak menjadi visualisasi utama. Jika payload hanya berisi satu status `OK`, tampilkan sebagai `Rekonsiliasi: Terverifikasi` dengan penjelasan singkat.

## Kontrak copy dan data display

- Hapus prefix tampilan `SILARAS |` dari judul kartu; brand tetap berada di topbar.
- Gunakan `Klaster Kegiatan`, bukan `Cluster Kegiatan`.
- Map key teknis ke label: `uraian_detail` → `Uraian detail`, `harga_satuan` → `Harga satuan`, `source_file` → `Sumber data`, `total_detail` → `Total detail`, `total_rekap` → `Total rekap`.
- `Jumlah item`, `Jumlah IKU`, `Jumlah kegiatan`, `Kuantitas`, dan `Selisih` tidak memakai Rupiah kecuali memang kolom nominal.
- Nama file sumber tetap exact untuk audit lineage; hanya label kolomnya yang dilokalkan.
- Nilai `OK`, `WARN`, dan status mapping ditampilkan sebagai status manusiawi/badge tanpa mengubah payload asli.

## State dan aksesibilitas

- Pertahankan loading, empty, partial/error, refresh, theme, sorting, searching, pagination, dan filter tahun.
- Gunakan skeleton/inline loading yang seukuran konten, bukan layout yang meloncat.
- Pertahankan `focus-visible`, `aria-label`, semantic `main/section/table`, dan kontras yang dapat dibaca.
- Motion hanya pada opacity/transform dengan durasi singkat; hormati `prefers-reduced-motion`.

## Batasan teknis

- Pertahankan vanilla JS, ECharts, Flask proxy, endpoint, cache, dan lineage data.
- Tidak menjalankan pipeline, upload, Airflow trigger, publish, atau mengubah data Gold.
- Perubahan harus kecil dan dapat di-review; tidak menambah library hanya untuk polish.

## Kriteria penerimaan

1. URL/surface yang diuji memuat bundle terbaru; tidak ada screenshot yang masih memakai markup lama.
2. Tidak ada judul kartu yang diawali `SILARAS |`.
3. Tidak ada underscore pada header tabel yang terlihat.
4. Kolom jumlah menampilkan angka biasa; kolom nominal menampilkan Rupiah.
5. Status satu baris tidak memakan satu kartu analitik penuh.
6. Hierarki KPI jelas dengan Total Anggaran sebagai fokus utama.
7. Layout tetap terbaca pada viewport desktop dan mobile tanpa horizontal overflow halaman.
8. Console browser bersih; test unit, bridge, dan Playwright lulus.
