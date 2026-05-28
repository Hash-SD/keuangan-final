# CHECKPOINT-UI-04: Beranda Page

## Tujuan
Membuat halaman Beranda final sebagai ringkasan kondisi sistem lokal.

## File Dibaca
- `portal/index.html`
- `outputs/metrics/reconcile_control_total.json`
- `outputs/metrics/data_quality_score.json`
- `stitch_uc_data_portal_design/beranda_portal_keuangan_lakehouse_v2/code.html`

## Dokumentasi Context7 yang Dibaca
- Tailwind CSS: card grid dan responsive layout.
- MDN Web Docs: semantic section dan table layout.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada UI-00.

## File Dibuat/Diubah
- `portal/index.html`
- `docs/checkpoints/CHECKPOINT-UI-04-beranda-page.md`

## Implementasi
Beranda memuat:
- Welcome section.
- Total Piutang UKT: Rp31.250.000.
- Jumlah Mahasiswa Penunggak: 15.
- Data Quality Score: 100%.
- Pipeline Status: Success.
- Last Run: 26 Mei 2026, 10:42 WIB.
- Pipeline Flow: Upload Data, Quality Gate, Bronze, Silver, Gold, Trino, Superset, Evaluasi.
- Aktivitas Terakhir.

## Command yang Dijalankan
```bash
Invoke-WebRequest -Uri http://localhost:8090 -UseBasicParsing
```

## Hasil Validasi
- Beranda memakai shell global.
- Angka kontrol sesuai repo.
- Pipeline flow tampil rapi.
- Tidak ada top navigation.

## Masalah / Risiko
- Last run masih memakai nilai kontrol statis sesuai instruksi, bukan timestamp otomatis.

## Keputusan Teknis
- Metrik membaca output lokal jika tersedia, tetapi fallback tetap angka kontrol repo.

## Langkah Berikutnya
Lanjut `CHECKPOINT-UI-05-data-page.md`.

## Status
Selesai
