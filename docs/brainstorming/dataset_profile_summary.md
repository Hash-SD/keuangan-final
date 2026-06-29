# Dataset Profile Summary - Excel RAB, RPD, IKU, Nomenklatur

Profil detail tersimpan di:

- `outputs/reports/dataset_profile_2023.json`
- `outputs/reports/dataset_profile_2024.json`
- `outputs/reports/dataset_profile_2025.json`
- `outputs/reports/dataset_profile_nomenklatur.json`

## RAB 2025

Workbook: `D:\Downloads\RAB 2025 SD RAB IKU.xlsx`

Sheet utama:

- `RAB`: sumber utama item anggaran berbasis warna dan hirarki.
- `RPD`: sumber rencana penarikan dana, mirip struktur RAB tetapi lebih lebar sampai kolom bulanan.
- `master akun`, `master IKU`, `ket_akun`: referensi akun dan IKU.
- `Rekap + Komen FS`: rekap dan catatan audit.
- Sheet rincian akun seperti `jasa profesi - ok`, `perjalanan dinas - ok`, `belanja bahan`, dan sejenisnya: audit/detail pendukung.

Warna penting:

- `FF92D050`: akun/jenis belanja.
- `FFFFFF00`: nomenklatur/program/output/komponen.
- `FFFF0000`: kegiatan/subkomponen besar.
- `FF00B0F0`: unit/prodi/pelaksana.
- `FFD8D8D8` dan `FFBFBFBF`: header.

Risiko parsing:

- Banyak baris kosong secara visual tetapi membawa konteks dari baris berwarna sebelumnya.
- Formula dan merge perlu disimpan di Bronze untuk audit.
- RPD memiliki kolom lebih lebar dari RAB sehingga parser tidak boleh mengunci kolom sampai N saja.

## RAB 2024

Workbook: `D:\Downloads\Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx`

Sheet utama:

- `REKAP`: kontrol total per akun.
- `USULAN PROKER SD`: konteks program kerja dan IKU.
- Sheet kegiatan seperti `PKS`, `SG & Kuliah Tamu`, `Belanja ATK`, `Sertifikasi Spark`, `Promosi Prodi`, dan lain-lain: detail item.

Temuan profil:

- `REKAP` memiliki banyak merged range dan formula.
- `USULAN PROKER SD` memiliki banyak warna non-standar sehingga lebih cocok sebagai konteks/mapping, bukan tabel rigid.
- Sheet detail bervariasi ukurannya; beberapa kecil, beberapa sampai ratusan baris karena area format kosong.

Risiko parsing:

- Nama sheet sering menjadi konteks kegiatan, tetapi tidak boleh menjadi satu-satunya sinyal.
- Beberapa sheet menggunakan warna blok lokal, bukan mapping warna RAB 2025.
- Total detail vs rekap bisa berbeda sehingga validasi harus menghasilkan `REVIEW`, bukan gagal total.

## RAB 2023

Workbook:

- `D:\Downloads\RAB_SD_Usulan KE (1)_Jan-Jun 2023.xlsx`
- `D:\Downloads\RAB_SD_Usulan KE (1)_jul-des 2023.xlsx`

Sheet utama:

- `REKAP`: kontrol total.
- `Prioritas Kegiatan`: konteks kegiatan, periode, dan IKU.
- Sheet akun belanja seperti `Belanja Bahan (521211)`, `Belanja Jasa Profesi (522151)`, `Belanja Sewa (522141)`, dan lain-lain: item detail.

Temuan profil:

- Tahun 2023 terdiri dari dua file periode dan wajib digabung sebagai satu tahun anggaran.
- Header item umumnya berisi kata `Uraian`, `QTY`, `Harga`, `Total/Jumlah`.
- Kode akun sering tersedia di nama sheet.
- Formula dan merged range muncul di banyak sheet.

Risiko parsing:

- Jika hanya satu file periode diproses, total tahunan salah.
- Cell kosong sering berarti pewarisan konteks, bukan data hilang.
- Sheet `Prioritas Kegiatan` harus dipakai untuk mapping IKU/kegiatan, bukan untuk item detail.

## Nomenklatur

Workbook: `D:\Downloads\Nomenklatur.xlsx`

Sheet utama:

- `Nomenklatur FS`

Warna penting:

- `FFB4A7D6`: Kegiatan.
- `FFF6B26B`: KRO.
- `FF93C47D`: RO.
- `FF76A5AF`: Komponen.
- `FFC27BA0`: Sub Komponen.
- Putih/tanpa warna: Detail Kegiatan.

Temuan profil:

- Sheet memiliki 1000 baris dan 27 kolom, tetapi area penting awal berpusat di kolom B-F.
- Ada 52 merged ranges.
- Top color juga mencakup `FF92D050`, `FFCAEDFB`, dan `FFFAE2D5`, sehingga parser perlu warning untuk warna tidak dikenal.

Risiko parsing:

- Detail kegiatan tanpa parent aktif harus ditandai warning.
- IKU bisa berisi beberapa kode dan harus dipecah dengan allocation weight.
- Key join tidak boleh hanya nama detail kegiatan; harus menyertakan path hierarki.

## Sheet Pipeline vs Audit

Pipeline utama:

- 2025: `RAB`, `RPD`, `master akun`, `master IKU`.
- 2024: `REKAP`, `USULAN PROKER SD`, semua sheet detail kegiatan.
- 2023: `REKAP`, `Prioritas Kegiatan`, semua sheet akun/detail.
- Nomenklatur: `Nomenklatur FS`.

Audit/pendukung:

- Sheet contoh, komentar, dan rincian akun tetap diekstrak ke Bronze.
- Sheet tampilan manusia tidak boleh menjadi satu-satunya sumber Gold.

## Prinsip Parser

- Bronze menyimpan semua cell, formula, warna, merge, sheet, row, column, dan lineage.
- Silver membaca struktur dengan stateful context dari atas ke bawah.
- Nama file hanya sinyal pendukung; tahun berasal dari isi workbook dan fallback metadata upload.
- Gold hanya `fact_anggaran`, dengan `jumlah_weighted_iku` agar visualisasi IKU tidak double-count.
