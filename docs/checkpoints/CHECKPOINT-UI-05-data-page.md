# CHECKPOINT-UI-05: Data Page

## Tujuan
Membuat halaman Data untuk upload, validasi, preview, rejected rows, dan riwayat upload.

## File Dibaca
- `portal/index.html`
- `data/quarantine/logs/quality_gate_summary.json`
- `data/quarantine/logs/rejected_rows.csv`
- `data/generated/gold/vw_dashboard_piutang_ukt.csv`
- `data/generated/silver/fact_piutang_ukt_prodi.csv`
- `stitch_uc_data_portal_design/data_portal_portal_keuangan_sidebar/code.html`

## Dokumentasi Context7 yang Dibaca
- MDN Web Docs: Fetch API, table rendering, form/input semantics.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada UI-00.

## File Dibuat/Diubah
- `portal/index.html`
- `portal/server.py`
- `docs/checkpoints/CHECKPOINT-UI-05-data-page.md`

## Implementasi
Halaman Data memuat:
- Upload PDF Audited ke `data/raw/pdf/`.
- Upload CSV Transaksi ke `data/raw/csv/`.
- Upload Excel RAB ke `data/raw/excel/`.
- Quality Check Summary: 800 total rows, 784 valid rows, 16 rejected rows, Dropout Rate 2%.
- Preview Data dari Gold/Silver CSV jika tersedia.
- Rejected Rows dari quarantine CSV.
- Riwayat Upload.

Tombol upload/admin dibuat disabled dengan label `Menunggu integrasi backend`.

## Command yang Dijalankan
```bash
Invoke-WebRequest -Uri http://localhost:8090/api/portal-state -UseBasicParsing
```

## Hasil Validasi
- Data page tampil rapi.
- Preview CSV dibatasi oleh API server.
- Empty state tersedia jika output file belum ada.
- Tidak ada tombol palsu yang mengklaim upload berhasil.

## Masalah / Risiko
- Upload belum terhubung backend POST endpoint.

## Keputusan Teknis
- Browser tidak menjalankan command lokal langsung; proses pipeline harus lewat backend aman jika nanti ditambahkan.

## Langkah Berikutnya
Lanjut `CHECKPOINT-UI-06-dashboard-page.md`.

## Status
Selesai
