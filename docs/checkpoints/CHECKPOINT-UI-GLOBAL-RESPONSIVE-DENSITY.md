# CHECKPOINT-UI-GLOBAL-RESPONSIVE-DENSITY

## Tujuan
Memperbaiki layout seluruh halaman Portal Keuangan agar content area tidak terkunci sempit di tengah, memakai lebar sisa setelah sidebar secara proporsional, tetap rapi di desktop 100%, dan tetap masuk akal pada kondisi zoom-out atau viewport lebar.

## Masalah Awal
- Dashboard sempit di tengah.
- Data sempit di tengah.
- Orkestrasi terpotong dan DAG Name pecah.
- System service cards terlalu kecil.
- Zoom 67% tidak memperbaiki layout karena container terkunci.
- URL route format `#/data`, `#/dashboard`, dan route lain jatuh ke Beranda karena router hanya menerima `#data`.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil

## Skill yang Dicari
- docker
- ssh
- shell
- python
- backend
- frontend
- testing
- ui
- responsive
- browser

## Skill yang Dipakai
- frontend
- ui
- responsive
- browser
- testing
- shell

## Alasan Pemilihan Skill
Skill `frontend`, `ui`, dan `responsive` dipakai karena checkpoint ini memperbaiki layout shell, page wrapper, grid, card sizing, table overflow, pipeline flow, dan responsive behavior semua halaman.

Skill `browser` dipakai karena hasil harus divalidasi di `http://localhost:8090` pada route utama dengan viewport desktop, tablet, dan mobile serta console error.

Skill `testing` dan `shell` dipakai karena validasi dilakukan melalui PowerShell, server lokal, Python compile, dan pytest.

## Dokumentasi Context7 yang Dibaca
- Tailwind CSS (`/tailwindlabs/tailwindcss.com`): responsive design, max-width/container utility, grid, flex, dan overflow utilities.
- MDN Web Docs (`/mdn/content`): CSS Grid, Flexbox, max-width, overflow-x, responsive layout, dan media query behavior.
- Playwright (`/microsoft/playwright`): viewport size, screenshot, dan console message/error validation.

## File Dibaca
- `portal/index.html`
- `portal/server.py`
- `scripts/start_portal.ps1`
- `.agents/skills/find-skills/SKILL.md`
- Browser skill: `C:\Users\hm\.codex\plugins\cache\openai-bundled\browser\26.519.41501\skills\browser\SKILL.md`
- Browser viewport docs: `C:\Users\hm\.codex\plugins\cache\openai-bundled\browser\26.519.41501\docs\capabilities\browser\viewport.md`

## File Diubah
- `portal/index.html`
- `docs/checkpoints/CHECKPOINT-UI-GLOBAL-RESPONSIVE-DENSITY.md`

## Perubahan Global
- Mengganti `.content` dari `width: min(1280px, calc(100% - 4rem))` menjadi wrapper global `width: 100%`, `max-width: 1680px`, dan padding responsif.
- Membuat `.app-main` sebagai flex column dengan footer-safe spacing.
- Menambahkan grid global khusus:
  - `.home-metrics-grid`
  - `.data-quality-grid`
  - `.dashboard-metrics-grid`
  - `.dashboard-flow-grid`
  - `.orchestration-summary-grid`
  - `.orchestration-body-grid`
  - `.system-services-grid`
  - `.analytics-top-grid`
  - `.lakehouse-validation-grid`
- Membuat table dan flow overflow internal melalui `.table-wrap`, `.table-preview`, `.table-wide`, `.table-compact`, `.pipeline-flow`, dan `.lineage-flow`.
- Memperbesar min-width internal pipeline flow agar stepper panjang tidak memaksa body overflow.
- Menambahkan `html/body` width/min-height dan menjaga `body overflow-x: hidden`.
- Menambahkan helper `formatDuration()` agar latency tidak tampil sebagai angka detik mentah.
- Menormalisasi router hash agar `#/beranda`, `#/data`, `#/dashboard`, `#/lakehouse`, `#/orkestrasi`, `#/analytics`, dan `#/system` bekerja.

## Perubahan Per Halaman
### Beranda
- Metric cards memakai `.home-metrics-grid`.
- Pipeline flow dan activity table tetap full width dengan overflow internal.

### Data
- Quality Check Summary dan Preview Data memakai `.data-quality-grid` 35/65 pada desktop.
- Preview table memakai min-width internal 960px.
- Rejected Rows dan Riwayat Upload memakai table overflow internal.

### Dashboard
- Metric cards memakai `.dashboard-metrics-grid`.
- Pipeline Data Flow dan Superset Section memakai `.dashboard-flow-grid` 70/30.
- Pipeline Latency diformat human-readable.
- Last Activity tetap full width.

### Lakehouse
- Bronze/Silver/Gold tetap 3 kolom desktop.
- Data Lineage tetap full width dengan overflow internal.
- Layer History dan Validate Gold memakai `.lakehouse-validation-grid`.

### Orkestrasi
- Control panel dibuat full width dengan `.control-panel` dan `.control-actions`.
- Tombol pipeline wrap rapi.
- DAG summary memakai `.orchestration-summary-grid` dengan DAG Name lebih lebar.
- DAG Name memakai monospace, ukuran lebih kecil, dan break-word.
- Pipeline Execution Flow dan Task Instance Detail memakai `.orchestration-body-grid` 70/30.
- Task table memakai `.table-compact`.
- Logs panel full width dan fixed readable height.

### Analytics
- Superset Status dan UAT Score Summary memakai `.analytics-top-grid`.
- UAT Form dan UAT History tetap full width.

### System
- Service cards memakai `.system-services-grid` 4 kolom pada desktop besar, 3 kolom pada desktop sedang, 2 kolom pada laptop/tablet, 1 kolom mobile.
- Service cards menampilkan Host Port, Container Port, URL, dan Credential.
- PostgreSQL tetap memakai Copy Connection.
- Audit Trail tetap full width.

## Command yang Dijalankan
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
npx skills find docker
npx skills find ssh
npx skills find shell
npx skills find python
npx skills find backend
npx skills find frontend
npx skills find ui
npx skills find responsive
npx skills find browser
npx skills find testing
python -m py_compile portal/server.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_portal.ps1
python -m pytest tests/ -v
```

## Hasil Validasi
- `python -m py_compile portal/server.py`: sukses.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_portal.ps1`: sukses, portal aktif di `http://localhost:8090`.
- `python -m pytest tests/ -v`: 8 passed.
- Browser route validation:
  - `http://localhost:8090/#/beranda`: route benar, no console error, no body overflow-x.
  - `http://localhost:8090/#/data`: route benar, no console error, no body overflow-x.
  - `http://localhost:8090/#/dashboard`: route benar, no console error, no body overflow-x.
  - `http://localhost:8090/#/lakehouse`: route benar, no console error, no body overflow-x.
  - `http://localhost:8090/#/orkestrasi`: route benar, no console error, no body overflow-x, DAG Name tidak pecah buruk.
  - `http://localhost:8090/#/analytics`: route benar, no console error, no body overflow-x.
  - `http://localhost:8090/#/system`: route benar, no console error, no body overflow-x.

## Validasi Visual
- 100% zoom: divalidasi melalui viewport desktop normal 1366x768; content memakai lebar sisa setelah sidebar dan tidak terkunci 1280px.
- 90% zoom: divalidasi sebagai kondisi intermediate melalui responsive viewport desktop dan tidak ada overflow-x.
- 80% zoom: divalidasi sebagai kondisi intermediate melalui responsive viewport desktop dan tidak ada overflow-x.
- 67% zoom: in-app Browser tidak mengekspos kontrol zoom aktual; shortcut zoom dicoba tetapi DPR/innerWidth tidak berubah. Validasi pengganti dilakukan dengan viewport lebar 1920x1080 yang meniru ruang CSS lebih luas setelah zoom-out. Hasilnya page content mencapai sekitar 1617px, no console error, dan no body overflow-x.

## Validasi Responsive
- 1920x1080: semua route memakai content width sekitar 1617px, tidak sempit, no body overflow-x.
- 1366x768: semua route memakai sisa lebar setelah sidebar sekitar 1063px, no body overflow-x.
- Tablet 820x1180: sidebar menjadi horizontal/top layout, semua halaman stack rapi, table/flow scroll internal, no body overflow-x.
- Mobile 390x844: semua halaman 1 kolom, table/flow scroll internal, no body overflow-x.

## Error yang Ditemukan
- Router tidak mendukung URL `#/route`; route tersebut jatuh ke Beranda.
- Page wrapper `.content` terlalu sempit karena `width: min(1280px, calc(100% - 4rem))`.
- Dashboard, Data, Orkestrasi, dan System memakai grid umum yang kurang sesuai untuk area desktop luas.
- DAG Name berada di metric card sempit sehingga berisiko pecah buruk.
- Pipeline flow dan table panjang belum punya standar min-width internal yang konsisten.

## Perbaikan yang Dilakukan
- Router hash dinormalisasi dengan pola `#/route` dan `#route`.
- Wrapper global diperluas menjadi max-width 1680px.
- Grid per halaman dibuat lebih adaptif.
- Table dan pipeline flow dibuat overflow internal.
- DAG Name diperbaiki dengan width lebih besar dan styling teks khusus.
- Service cards System diperlebar dan informasi port dibuat lebih eksplisit.

## Masalah Tersisa
- Browser in-app tidak memberikan cara pasti untuk menetapkan zoom browser aktual 67%; validasi 67% dicatat sebagai viewport luas/zoom-out equivalent dan percobaan shortcut zoom tidak mengubah DPR.
- File lain di worktree sudah berubah sebelum checkpoint ini (`README.md`, `portal_backend/services/system_status.py`, `scripts/check_ports.ps1`) dan tidak disentuh dalam revisi UI ini.

## Status
Selesai
