# CHECKPOINT-BE-MAIN-00: Context Alignment

## Tujuan
Menyelaraskan backend Portal Keuangan dengan konsep utama pada `main.pdf`.

## File Dibaca
- main.pdf
- README.md
- Makefile
- portal_backend/
- docs/checkpoints/CHECKPOINT-BE-*.md

## Dokumentasi Context7 yang Dibaca
- Flask: routing, JSON response, file upload, static frontend serving.
- Python/cpython: `subprocess.run`, `pathlib`, `json`, dan `csv`.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- Belum ada pada checkpoint ini.

## Implementasi
Konteks `main.pdf` yang dipakai:
- Sumber data: 1 PDF audited, 2 CSV transaksi, 1 Excel RAB.
- Nilai kontrol: Rp31.250.000, 15 mahasiswa penunggak, Rp150.000.000 RAB.
- Layer: Bronze, Silver, Gold.
- Metrik: Pipeline Latency, Data Freshness, Dropout Rate, Data Quality Score.
- UAT utama: Navigation Facility, Clarity of Visualization, Data Relevance, Usefulness in Decision Making.

## Command yang Dijalankan
```bash
python - <<'PY'
from pypdf import PdfReader
reader = PdfReader("main.pdf")
print(len(reader.pages))
PY
```

## Hasil Validasi
`main.pdf` dapat dibaca dengan programmatic text extraction tanpa OCR.

## Masalah / Risiko
`main.pdf` dan sample PDF masih untracked lokal, sehingga endpoint harus aman jika file tidak ada pada mesin lain.

## Keputusan Teknis
Backend tetap Flask dan tetap menjalankan script pipeline repo, bukan membuat pipeline baru.

## Langkah Berikutnya
Menambahkan endpoint status PDF/CSV/Excel.

## Status
Selesai
