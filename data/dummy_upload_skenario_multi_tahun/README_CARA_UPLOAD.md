# Paket Dummy Upload Multi Tahun

Folder ini berisi data dummy tambahan untuk mencoba upload manual pada portal. Setiap subfolder adalah satu skenario tahun akademik dan berisi PDF, dua CSV transaksi, serta Excel RAB.

## Cara pakai

1. Pilih salah satu folder `ta_YYYY_YYYY`.
2. Upload file PDF dari folder `pdf`.
3. Upload `transaksi_ganjil.csv` dan `transaksi_genap.csv` dari folder `csv`.
4. Upload file RAB dari folder `excel`.
5. Jika ingin dashboard dan validasi mengikuti skenario itu, samakan `.env` dengan nilai pada `manifest_skenario.csv`: `PORTAL_TARGET_TAHUN_AKADEMIK`, `PORTAL_TARGET_TAHUN_ANGGARAN`, `PORTAL_BATCH_ID`, `PORTAL_TARGET_TOTAL_PIUTANG`, `PORTAL_TARGET_JUMLAH_PENUNGGAK`, dan `PORTAL_TARGET_TOTAL_PAGU_RAB`.

## Catatan

- Format kolom dibuat mengikuti generator dan kontrak pipeline proyek saat ini.
- Sebagian baris CSV sengaja invalid sesuai kolom `invalid_rows_direncanakan` untuk menguji Quality Gate.
- Data bersifat sintetis/dummy dan tidak berisi data mahasiswa riil.
