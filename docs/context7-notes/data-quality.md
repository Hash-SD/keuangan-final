# Context7 Notes: Data Quality

Sumber Context7: `/pandas-dev/pandas` dan `/jsvine/pdfplumber`.

- `pdfplumber` cocok untuk digital-born PDF dan tidak menyediakan OCR; ini sesuai instruksi tanpa OCR.
- Gunakan `extract_text` untuk teks halaman dan `extract_table`/`extract_tables` untuk tabel.
- pandas dapat membaca CSV/Excel, melakukan coercion numerik dengan `pd.to_numeric(errors="coerce")`, dan tanggal dengan `pd.to_datetime(errors="coerce")`.
- Data wide Excel dapat diubah menjadi long format dengan `melt`.

Implikasi proyek:

- Quality gate menandai NIM kosong, nominal invalid, tanggal invalid, dan status tidak dikenal.
- Baris invalid masuk quarantine dengan log error terstruktur.
- Rekonsiliasi Gold wajib memeriksa total piutang Sains Data dan jumlah penunggak.

