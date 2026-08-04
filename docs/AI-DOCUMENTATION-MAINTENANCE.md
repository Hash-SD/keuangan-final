# Prosedur Pemeliharaan Dokumentasi AI

Dokumen ini membuat peta codebase tetap sinkron setelah kode berubah. Dokumentasi adalah artefak pemeliharaan; ia harus berubah bersama kontrak yang diubah, bukan hanya saat ada fitur besar.

## Aturan inti

- `CONTEXT.md` hanya berisi bahasa domain dan istilah kanonik.
- `docs/AI-CODEBASE-GUIDE.md` berisi struktur, alur, kontrak, source-of-truth, dan ambiguitas implementasi.
- `README.md` berisi orientasi pengguna dan command yang dapat dijalankan.
- Test adalah bukti kontrak yang berlaku. Jika README, kode, dan test berbeda, tandai perbedaannya dan jangan menyembunyikannya.
- Setiap commit yang mengubah kontrak runtime harus memperbarui dokumentasi pada perubahan yang sama.

## Trigger pembaruan

| Perubahan kode | Wajib periksa/perbarui |
|---|---|
| `src/parser_flexible/`, `src/excel_ingestion/` | bagian Bronze/Parsing, aturan workbook, lineage, test parser |
| `src/transformations/`, `src/gold/` | alur pipeline, grain Gold, output, quality gate, domain terms |
| `src/validation/` | kontrak dataset, publish guard, known risk, test map |
| `src/sql/`, `config/trino/`, `config/superset/` | publish PostgreSQL/Trino/Superset, schema, credential/env names tanpa nilai rahasia |
| `dags/` | urutan task, stage grouping, `dag_run.conf`, command aktual |
| `portal_backend/app.py` atau `portal_backend/services/` | tabel endpoint, side effect, status source, auth, fallback |
| `portal/v2/`, `portal/local-dashboard/` | sumber data frontend, polling, view/page, escaping, endpoint contract |
| `superset-dashboard/` | proxy flow, endpoint, cache, deployment/runtime port |
| `docker-compose.yml`, `*.ps1`, `Makefile`, `package.json` | service/port/command map dan safe verification command |
| `tests/` | test map dan kontrak yang menjadi bukti baru |
| istilah domain baru | `CONTEXT.md` sebelum istilah dipakai luas |

## Workflow saat membuat perubahan

### Sebelum mengubah kode

1. Baca `AGENTS.md`, `CONTEXT.md`, `docs/AI-CODEBASE-GUIDE.md`, dan file test area.
2. Jalankan `git status --short` untuk memastikan perubahan pengguna tidak tertimpa.
3. Catat kontrak yang harus tetap berlaku: source identity, path, schema, endpoint, status, dan side effect.
4. Untuk perubahan kompleks, tulis rencana kecil di issue/spec yang sudah ada; jangan membuat top-level doc baru jika lokasi yang tepat sudah tersedia.

### Setelah mengubah kode

1. Perbarui bagian guide yang dipetakan oleh tabel trigger.
2. Jika vocabulary berubah, perbarui `CONTEXT.md` dengan istilah kanonik dan `_Avoid_`.
3. Perbarui `README.md` hanya bila command atau perilaku pengguna berubah.
4. Tambahkan/ubah test yang membuktikan kontrak baru; jangan hanya mengubah dokumentasi agar cocok dengan bug.
5. Perbarui tabel “Status dokumen” pada guide: commit baseline, tanggal snapshot, dan ambiguitas yang terselesaikan.
6. Jalankan verifikasi yang proporsional dan catat command yang benar-benar dijalankan.
7. Periksa `git diff --check` dan pastikan diff source/data/config tidak muncul jika task hanya dokumentasi.

## Workflow khusus task dokumentasi-only

Untuk membaca repository tanpa mengganggu sistem berjalan:

1. Gunakan inspeksi read-only: `git status`, listing file, pencarian simbol, pembacaan source/test/docs.
2. Jangan menyalakan service, mengubah pointer aktif, upload workbook, trigger DAG, menulis manifest, atau menjalankan full pipeline.
3. Tulis hanya file dokumentasi yang disepakati.
4. Validasi Markdown secara tekstual dan `git diff --check`.
5. Laporkan dengan jelas bahwa validasi runtime tidak dilakukan jika lingkungan hidup memerlukannya.

## Checklist review AI sebelum commit

- [ ] Peta file dan entry point masih benar.
- [ ] Semua endpoint yang ditambah/dihapus sudah tercatat.
- [ ] Dataset/run identity dan status publish masih terdokumentasi.
- [ ] Grain Gold dan formula allocation masih akurat.
- [ ] Side effect filesystem/network disebutkan.
- [ ] Fallback legacy/ambiguity tidak tertulis sebagai fakta yang pasti.
- [ ] Tidak ada secret, token, isi `.env`, absolute local path, atau data pengguna.
- [ ] Test map mencakup test baru yang relevan.
- [ ] Baseline commit/tanggal snapshot diperbarui.
- [ ] Diff hanya menyentuh scope task.

## Cara menangani perubahan yang belum jelas

Jika dokumentasi lama, kode, dan test bertentangan:

1. nyatakan tiga sumber tersebut secara eksplisit;
2. gunakan implementasi + test sebagai “observed behavior” sementara;
3. tandai bagian itu di “Ambiguitas dan legacy”;
4. jangan mengubah perilaku hanya untuk membuat dokumen terlihat konsisten;
5. minta keputusan produk/arsitektur jika kontrak perlu dipilih ulang.

