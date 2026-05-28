# CHECKPOINT-PROCESS-00: Skill Finder dan Context7 Protocol

## Tujuan
Menetapkan aturan wajib untuk revisi global UI, audit Docker, backend API, dan final test agar setiap checkpoint mencatat skill finder, skill yang dipilih, dokumentasi Context7, command, validasi, error, perbaikan, dan status.

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
- find-skills
- frontend
- ui
- responsive
- browser
- testing
- docker
- ssh
- shell
- python
- backend

## Alasan Pemilihan Skill
Skill `find-skills` dipakai karena proses revisi berikutnya wajib mencari skill terlebih dahulu sebelum revisi layout, backend, Docker, atau pengujian end-to-end.

Skill `frontend`, `ui`, `responsive`, `browser`, dan `testing` dipakai untuk revisi global layout halaman Beranda, Data, Dashboard, Lakehouse, Orkestrasi, Analytics, dan System.

Skill `docker`, `ssh`, `shell`, dan `testing` dipakai untuk audit Docker Compose, status container, port mapping, init container, service healthcheck, dan duplicate container.

Skill `backend`, `python`, `shell`, dan `testing` dipakai untuk audit dan pengujian Flask/FastAPI style endpoint, subprocess pipeline runner, upload path handling, empty state, activity log, dan response JSON.

## Dokumentasi Context7 yang Dibaca
- Tailwind CSS (`/tailwindlabs/tailwindcss.com`): responsive utilities, grid, flex, max-width/container utilities, dan overflow behavior.
- Docker Compose (`/docker/compose`): `docker compose ps`, service status, port publishing, `depends_on` health handling, dan `docker compose start --wait`.
- pytest (`/pytest-dev/pytest`): command line test run, `-v`/`-vv`, failure report, dan assertion introspection.

## File Dibaca
- `C:\Users\hm\keuangan-final\.agents\skills\find-skills\SKILL.md`
- `C:\Users\hm\keuangan-final\docs\checkpoints\CHECKPOINT-UI-14-final-validation.md`
- `C:\Users\hm\keuangan-final\docs\checkpoints\CHECKPOINT-AUDIT-00-context7-skill-readiness.md`
- `C:\Users\hm\keuangan-final\docs\checkpoints\`

## File Diubah
- `C:\Users\hm\keuangan-final\docs\checkpoints\CHECKPOINT-PROCESS-00-skill-finder-context7-protocol.md`

## Command yang Dijalankan
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
npx skills find docker
npx skills find ssh
npx skills find shell
npx skills find python
npx skills find backend
npx skills find frontend
npx skills find testing
npx skills find ui
npx skills find responsive
npx skills find browser
```

## Hasil Validasi
- `find-skills` berhasil dipasang di `C:\Users\hm\keuangan-final\.agents\skills\find-skills`.
- Pencarian skill untuk semua kata kunci wajib berhasil dijalankan.
- Context7 berhasil resolve dan membaca dokumentasi resmi Tailwind CSS, Docker Compose, dan pytest.
- Format checkpoint baru sudah memasukkan bagian wajib: Skill Finder, Skill yang Dicari, Skill yang Dipakai, Alasan Pemilihan Skill, Dokumentasi Context7 yang Dibaca, File Dibaca, File Diubah, Command, Hasil Validasi, Error, Perbaikan, Masalah Tersisa, dan Status.

Ringkasan hasil pencarian skill:

- `docker`: hasil teratas `mindrally/skills@docker`.
- `ssh`: hasil teratas `openhands/skills@ssh`.
- `shell`: hasil teratas relevan `miles990/claude-software-skills@shell-bash`.
- `python`: hasil teratas `wshobson/agents@python-design-patterns`.
- `backend`: hasil relevan `customware-ai/skills@backend-integration`.
- `frontend`: hasil relevan `rand/cc-polymath@discover-frontend`.
- `testing`: hasil relevan `nishilbhave/codeprobe@codeprobe-testing`.
- `ui`: hasil teratas `lobehub/lobehub@react`.
- `responsive`: hasil teratas `hoodini/ai-agents-skills@mobile-responsiveness`.
- `browser`: hasil teratas `aradotso/trending-skills@agent-browser-automation`.

## Error yang Ditemukan
- Tidak ada error pada instalasi `find-skills`.
- Tidak ada error pada pencarian skill.
- Tidak ada error pada query Context7.
- Catatan risiko: beberapa hasil skill registry memiliki install count rendah atau scope tidak persis sama, sehingga pemilihan skill untuk checkpoint berikutnya tetap harus disesuaikan dengan kebutuhan checkpoint dan skill lokal yang tersedia.

## Perbaikan yang Dilakukan
- Menambahkan checkpoint protokol baru sebagai acuan proses untuk checkpoint berikutnya.
- Mencatat command wajib `find-skills`, daftar skill yang dicari, ringkasan skill relevan, dan dokumentasi Context7 resmi yang sudah dibaca.

## Masalah Tersisa
- Checkpoint lama belum diubah massal ke format baru agar tidak menyentuh banyak file tanpa kebutuhan checkpoint spesifik.
- Revisi global layout, audit Docker, backend API, dan final test belum dijalankan pada checkpoint ini.

## Status
Selesai
