# Portal V2 sebagai Portal Utama

## Tujuan

Menjadikan `portal/v2/index.html` sebagai tampilan utama SILARAS SD dengan tetap mempertahankan seluruh kemampuan operasional V1 dan menyediakan V1 sebagai fallback `/legacy`.

## Pengalaman Pengguna

- Beranda V2 menampilkan angka Total Anggaran, Weighted IKU, jumlah Gold, Quality Gate, dan status pipeline dari API nyata.
- Navigasi V2 mencakup Beranda, Upload, Orkestrasi, Lakehouse, Review IKU, Analytics/UAT, Dashboard, dan Status Sistem.
- Mode Ringkas menampilkan KPI inti; Mode Detail menampilkan lineage, sumber data, timestamp, task Airflow, dan alasan status.
- Status `success`, `running`, `failed`, `missing`, dan `unreachable` memakai warna dan label yang konsisten.
- Review IKU menjelaskan bahwa penyimpanan override belum mengubah Gold/database sampai pengguna menjalankan Orkestrasi → Jalankan Sistem.
- Dark mode, responsive layout, keyboard focus, dan error state dipertahankan dari konsep Apple UI V2.

## Arsitektur Integrasi

- Route `/` menyajikan V2.
- Route `/legacy` menyajikan V1 untuk fallback dan perbandingan.
- V2 memilih API backend secara dinamis: port backend eksplisit pada development lokal dan origin yang sama pada deployment reverse-proxy.
- Data dashboard membaca `/api/superset/summary`, `/api/metrics`, `/api/airflow/latest`, `/api/system-truth/status`, dan `/api/excel-lakehouse/status`.
- Semua aksi mutasi tetap memakai endpoint backend yang sama, dengan error ditampilkan pada komponen yang memicu aksi.
- Tidak ada status pipeline hardcoded; stepper dihitung dari artefak dan run terbaru.

## Keamanan dan Ketahanan

- Tidak ada token atau credential yang ditanam di HTML.
- Upload memakai validasi backend dan menampilkan progress/error yang dapat dipahami pengguna.
- Superset summary tidak boleh mengklaim lengkap jika query terkena batas baris.
- V1 tidak dihapus sampai smoke test V2 dan fallback selesai.

## Verifikasi

- Regression test kontrak HTML/API untuk route, API base, semua halaman inti, status color, dan instruksi Review IKU.
- Unit/integration test untuk mapping payload V2 dan fallback error.
- Browser smoke test untuk `/`, Upload, Orkestrasi, Lakehouse, Review IKU, Analytics, Dashboard, Status Sistem, serta `/legacy`.
- Endpoint smoke test memastikan angka live tidak kembali menjadi `-` ketika backend tersedia.
