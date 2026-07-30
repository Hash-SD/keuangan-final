# Analisis akar penyebab ketiadaan timestamp freshness

T0, T1, dan T2 historis tidak dapat dipasangkan untuk bundle RAB kanonis `upload-2026-06-09-011818-37cc4d`.

- T0: log aktivitas mencatat peristiwa unggah, tetapi hanya menyimpan target unggahan. Log tersebut tidak menyimpan `dataset_session_id` yang dapat dipasangkan dengan bundle Gold kanonis.
- T1: metadata `data/generated/excel_lakehouse_metadata.json` menyimpan `run_id`, jumlah baris, dan `dataset_session_id`, tetapi tidak menyimpan `gold_finished_at`.
- T2: endpoint dashboard hanya memberikan `generated_at` ketika API dibaca. Nilai tersebut adalah waktu respons pemeriksaan, bukan waktu dataset dashboard tersedia setelah run historis.

Timestamp objek MinIO tidak digunakan sebagai pengganti T0--T2 karena objek metadata historis yang memuat konteks dummy telah dihapus dan waktu modifikasi objek tidak membuktikan waktu penyelesaian dashboard. Karena ketiga timestamp tidak berasal dari satu run yang sama, menghitung freshness akan menghasilkan angka lintas-sesi yang menyesatkan.

Tindakan perbaikan operasional yang diperlukan: setiap unggahan harus menyimpan `dataset_session_id` dan `submitted_at`; pipeline harus menyimpan `gold_finished_at`; dan pembaruan dataset dashboard harus menyimpan `dashboard_available_at` dengan `dataset_session_id` yang sama.
