# CHECKPOINT-UI-02: Shell Layout

## Tujuan
Membuat layout utama reusable untuk seluruh halaman: left sidebar, main content, sticky header, dan footer global.

## File Dibaca
- `portal/index.html`
- `stitch_uc_data_portal_design/beranda_portal_keuangan_left_sidebar/code.html`
- `stitch_uc_data_portal_design/beranda_portal_keuangan_lakehouse_v2/code.html`

## Dokumentasi Context7 yang Dibaca
- Tailwind CSS: pola `fixed`, `sticky`, responsive sidebar, grid, spacing.
- MDN Web Docs: semantic `aside`, `main`, `header`, `footer`, media query responsive.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada UI-00.

## File Dibuat/Diubah
- `portal/index.html`
- `docs/checkpoints/CHECKPOINT-UI-02-shell-layout.md`

## Implementasi
- Sidebar kiri fixed dengan lebar 18rem.
- Main content memakai offset `margin-left: var(--sidebar-width)`.
- Header halaman sticky di bagian atas main content.
- Footer global fixed di bawah dengan `left: var(--sidebar-width)`.
- Menu sidebar: Beranda, Data, Dashboard, Lakehouse, Orkestrasi, Analytics, System.
- Active menu berbasis hash route.

## Command yang Dijalankan
```bash
Select-String -Path portal/index.html -Pattern "app-sidebar|app-header|app-footer"
```

## Hasil Validasi
- Semua halaman memakai shell yang sama.
- Tidak ada top navigation menu utama.
- Footer tidak menutupi sidebar dan offset kiri sama dengan sidebar.

## Masalah / Risiko
- Pada mobile, sidebar fixed tidak cocok; dibuat responsive menjadi sticky/top horizontal nav.

## Keputusan Teknis
- Shell dibuat di satu file SPA agar sidebar/header/footer tidak terduplikasi antar halaman.

## Langkah Berikutnya
Lanjut `CHECKPOINT-UI-03-global-style-components.md`.

## Status
Selesai
