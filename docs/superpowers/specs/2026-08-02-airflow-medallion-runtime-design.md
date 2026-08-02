# Airflow Medallion Runtime Design

## Tujuan

Menampilkan durasi lima tahap Medallion berdasarkan data task-instance dari
Airflow, sehingga angka yang tampil di stepper sama dengan runtime pipeline
yang dipilih pengguna atau runtime yang sedang berjalan.

## Aturan sumber runtime

Sumber runtime dipilih dengan urutan berikut:

1. Run Airflow aktif dengan state `queued`, `running`, `scheduled`,
   `up_for_retry`, atau `up_for_reschedule`.
2. Run yang dipilih dari tabel `Eksekusi Pemrosesan Data`.
3. Run Airflow terakhir jika tidak ada pilihan dan tidak ada run aktif.

Run aktif selalu diutamakan agar tampilan proses yang sedang berjalan tidak
tertinggal oleh pilihan historis pengguna.

## Kalkulasi durasi

Backend memetakan task Airflow ke lima tahap Medallion. Durasi tahap adalah
jumlah durasi task yang tersedia dari respons Airflow. Untuk setiap task,
field `duration` digunakan terlebih dahulu. Jika field tersebut tidak tersedia,
selisih `start_date` dan `end_date` dari respons Airflow digunakan. Task yang
masih berjalan tidak memakai `Date.now()` atau waktu lokal browser; badge-nya
menampilkan spinner dan status berjalan sampai Airflow mengirim durasi final.
Jika seluruh durasi task dalam satu stage bernilai nol tetapi timestamp task
tersedia, stage memakai rentang timestamp Airflow terluas (`max(end_date)` -
`min(start_date)`) agar tahap EmptyOperator tetap memiliki runtime yang
terbaca.

Frontend hanya memilih run dan merender `duration_seconds` yang dikirim
backend. Frontend tidak menghitung ulang runtime.

## Error handling dan kompatibilitas

Jika endpoint task-instance tidak tersedia, status progress tetap tidak
tersedia dan UI menampilkan placeholder. Payload lama tanpa progress tetap
dirender tanpa membuat angka runtime sintetis.

## Verifikasi

- Unit test backend mencakup prioritas `duration`, fallback timestamp Airflow,
  task berjalan, dan agregasi tiap tahap.
- Runtime test Portal v2 mencakup prioritas run aktif di atas run terpilih dan
  tidak adanya kalkulasi berbasis `Date.now()` pada stepper.
