# 📊 Data Lakehouse Keuangan Prodi

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![Apache Spark](https://img.shields.io/badge/Apache_Spark-active-E25A1C.svg)
![Trino](https://img.shields.io/badge/Trino-SQL-DD00A1.svg)
![Superset](https://img.shields.io/badge/Apache_Superset-BI-20A7C9.svg)

Implementasi **Data Lakehouse** lokal berbasis *Medallion Architecture* (Bronze, Silver, Gold) untuk mengelola dan menganalisis data keuangan perguruan tinggi secara terpusat dan terukur. Proyek ini mengintegrasikan ekstraksi file kompleks (PDF, CSV, Excel) menjadi format *Star Schema* untuk visualisasi analitik akhir.

---

## 🎯 Target & Fungsionalitas Utama

1. **Synthetic Data Generation**: Menghasilkan data _dummy_ PDF terenkripsi (LKTA), CSV, dan Excel dengan relasi konsisten.
2. **Quality Gate Validation**: Mengevaluasi anomali data, memisahkan data _rejected_, dan menghitung _dropout rate_.
3. **Medallion Pipeline**: 
   - 🥉 **Bronze**: Ingestion raw data dari berbagai format.
   - 🥈 **Silver**: Cleansing, parsing, dan standarisasi.
   - 🥇 **Gold**: Pembentukan *Star Schema* agregasi (Iceberg & PostgreSQL).
4. **Data Stack Integration**: Menghubungkan Iceberg (MinIO) ke Trino Query Engine dan divisualisasikan via Apache Superset.

---

## 📂 Struktur Direktori

Berikut adalah arsitektur direktori utama pada repositori ini:

```text
keuangan-final/
├── config/          # Konfigurasi layanan (contoh: Trino, Spark, Superset)
├── dags/            # Script Apache Airflow DAGs untuk orkestrasi pipeline
├── data/            # Penyimpanan data lokal (raw, generated dummy, bronze layer)
├── docs/            # Dokumentasi proyek dan log pengembangan (checkpoints)
├── outputs/         # Hasil keluaran pipeline (metrik validasi, logs, Superset JSON)
├── portal/          # Source code UI Portal Keuangan Utama (Frontend HTML/JS)
├── portal_backend/  # Layanan API (Backend) untuk operasional portal web
├── scripts/         # Skrip otomatisasi PowerShell (start portal, full run, check ports)
├── src/             # Core Engine Data Lakehouse (Python)
│   ├── common/          # Utilitas bersama (path mapping, logging, time format)
│   ├── extraction/      # Modul parsing dokumen kompleks (e.g. PDF parsing)
│   ├── generators/      # Modul pembuat mock data / data sintetik terstruktur
│   ├── metrics/         # Penghitungan metrik kontrol kualitas dan pipeline latency
│   ├── sql/             # Skrip SQL untuk DDL Iceberg, query Trino, dan Postgres
│   ├── transformations/ # Logika pemrosesan Medallion (Bronze, Silver, Gold)
│   └── validation/      # Modul Quality Gate untuk memfilter bad data
├── tests/           # Unit test dan Integration test (pytest)
├── docker-compose.yml # Konfigurasi infrastruktur (MinIO, Spark, Trino, Postgres, Airflow)
└── README.md        # Dokumentasi utama proyek
```

---

## 🏗️ Nilai Kontrol Uji Coba

Untuk memastikan pipeline berjalan 100% akurat dan rekonsiliasi data lulus, sistem dipantau dengan batas kontrol berikut:

| Metrik Kontrol | Target Angka |
|:---|---:|
| **Total tunggakan UKT Prodi Sains Data** | `Rp 31.250.000` |
| **Jumlah mahasiswa penunggak Sains Data** | `15 Mahasiswa` |
| **Total pagu RAB Sains Data** | `Rp 150.000.000` |

Nilai di atas adalah default reproduksi data dummy Bab 4. Fokus sistem tetap Prodi Sains Data, tetapi periode dan nilai kontrol bisa diganti dari `.env` tanpa mengedit kode:

```env
PORTAL_TARGET_PRODI=Sains Data
PORTAL_TARGET_FAKULTAS=Fakultas Sains
PORTAL_TARGET_TAHUN_AKADEMIK=2024/2025
PORTAL_TARGET_TAHUN_ANGGARAN=2025
PORTAL_BATCH_ID=batch-sains-data-2025
PORTAL_TARGET_TOTAL_PIUTANG=
PORTAL_TARGET_JUMLAH_PENUNGGAK=
PORTAL_TARGET_TOTAL_PAGU_RAB=200000000
```

Jika `PORTAL_TARGET_TOTAL_PIUTANG` dan `PORTAL_TARGET_JUMLAH_PENUNGGAK` dikosongkan, rekonsiliasi berjalan dalam mode observasi untuk Sains Data pada tahun akademik aktif dan tidak terkunci ke nominal tertentu.

---

## 🚀 Quick Start (Local Environment)

### Prasyarat
- Python 3.11+
- Docker Desktop & Docker Compose
- Windows PowerShell (Opsional: `make` command)

### Langkah Menjalankan Pipeline Lengkap

1. **Persiapkan Konfigurasi Lingkungan:**
```powershell
Copy-Item .env.example .env
```

2. **Jalankan Infrastruktur Kontainer (Database, Storage, Engine):**
```powershell
docker-compose up -d
```

3. **Eksekusi End-to-End (Data Generation s/d Metrics UAT):**
```powershell
.\scripts\full_run.ps1
```

---

## 🌐 Service URLs (Akses Portal & Monitoring)

Sistem ini menyediakan antarmuka monitoring terpusat untuk setiap layanannya.

**Jalankan seluruh stack, termasuk Portal Induk dan Backend API:**
```powershell
docker compose up -d
```

Portal juga tetap dapat dijalankan secara lokal melalui `.\scripts\start_portal_backend.ps1` untuk kebutuhan debugging, tetapi mode normal proyek adalah melalui Docker Compose.

| Layanan | URL Akses | Kredensial Default | Deskripsi |
|---|---|---|---|
| **Portal Induk** | [http://localhost:8090](http://localhost:8090) | - | Akses semua tautan terpusat |
| **Backend API** | [http://localhost:8091/api/health](http://localhost:8091/api/health) | - | Status kesehatan sistem backend |
| **Apache Superset**| [http://localhost:8089](http://localhost:8089) | `admin` / `admin` | Dashboard Analitik UAT |
| **Apache Airflow** | [http://localhost:8085](http://localhost:8085) | `airflow` / `airflow` | Orkestrasi Workflow (DAGs) |
| **Trino Info** | [http://localhost:8082/v1/info](http://localhost:8082/v1/info) | - | Mesin Kueri Terdistribusi |
| **MinIO Console** | [http://localhost:9001](http://localhost:9001) | *Lihat di `.env`* | Object Storage (S3 API) |
| **Spark Master** | [http://localhost:8080](http://localhost:8080) | - | Klaster Spark UI |

> *Cek ketersediaan seluruh port yang digunakan proyek ini menggunakan skrip: `.\scripts\check_ports.ps1`*

---

## 🧪 Validasi Trino & Apache Iceberg

Hasil pemrosesan akhir (Gold Layer) dimuat sebagai tabel **Apache Iceberg** di dalam MinIO Object Storage, di mana metadata tabel diregistrasikan di PostgreSQL Metastore. 

Kueri validasi dapat dieksekusi secara langsung melalui Trino Engine:

```powershell
$tahun = (Get-Content .env | Select-String '^PORTAL_TARGET_TAHUN_AKADEMIK=').ToString().Split('=',2)[1]
docker exec keuangan-trino trino --catalog iceberg --schema gold --execute "SELECT o.nama_prodi, w.tahun_akademik, SUM(f.nominal_piutang_rp), COUNT(*) FROM fact_piutang_ukt_prodi f JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key JOIN dim_waktu_tunggakan w ON f.waktu_tunggakan_key = w.waktu_tunggakan_key WHERE o.nama_prodi = 'Sains Data' AND w.tahun_akademik = '$tahun' GROUP BY o.nama_prodi, w.tahun_akademik"
```
Query ini tetap fokus Sains Data, tetapi tahun akademiknya mengikuti `.env`.

---

## 📈 Integrasi Apache Superset

Skrip utama (`full_run.ps1`) dikonfigurasi untuk secara otomatis merakit *Database Connection* dan *Dataset* ke Superset via REST API:

- **Database Name**: `Trino Iceberg Gold Keuangan`
- **Dataset Target**: `vw_dashboard_piutang_ukt`
- **Dashboard Tersedia**: `Dashboard Piutang UKT Prodi`

Berkas JSON yang menampung ID aset BI terlacak pada:
- `outputs/reports/superset_assets.json`
- `outputs/reports/superset_dashboard.json`

---

## Storage Mapping Raw-Bronze-Silver-Gold

Pipeline memakai file lokal sebagai fallback pengembangan dan memetakan setiap layer ke prefix MinIO/S3 agar narasi lakehouse tetap dapat divalidasi secara eksplisit:

| Layer | Lokasi lokal | Prefix MinIO/S3 | Status |
| --- | --- | --- | --- |
| Raw | `data/raw` | `s3://lakehouse/raw/` | sumber PDF/CSV/Excel |
| Bronze | `data/generated/bronze` | `s3://lakehouse/bronze/` | hasil ingestion valid |
| Silver | `data/generated/silver` | `s3://lakehouse/silver/` | data clean/conformed |
| Gold | `data/generated/gold` | `s3://lakehouse/gold/` | star schema/dashboard view |
| Quarantine | `data/quarantine` | `s3://lakehouse/quarantine/` | rejected rows dan log validasi |
| Metrics | `outputs/metrics` | `s3://lakehouse/metrics/` | KPI teknis pipeline |
| Reports | `outputs/reports` | `s3://lakehouse/reports/` | manifest, Superset asset, bukti Bab 4 |
| Iceberg warehouse | - | `s3://lakehouse/warehouse/` | warehouse Iceberg terkonfigurasi |

Jalankan manifest storage:

```powershell
python src/storage/storage_manifest.py
```

Output utama:

- `outputs/reports/storage_mapping.json`
- `outputs/reports/storage_manifest.json`
- `outputs/reports/bab4_evidence_summary.json`

Secara default `MINIO_UPLOAD_ENABLED=false`, sehingga sistem menulis manifest lokal dan mapping S3 tanpa memerlukan MinIO aktif. Untuk mencoba upload aktual ke MinIO/S3-compatible storage, atur variabel berikut di `.env`:

```env
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=lakehouse
MINIO_SECURE=false
MINIO_UPLOAD_ENABLED=true
```

Mode upload membutuhkan dependency `boto3` dari `requirements.txt`. Jika upload gagal, manifest tetap dibuat dengan status jujur `mapped`, `partial`, atau `failed`.

---

## Portal dan Matriks UAT

Portal lokal tersedia di [http://localhost:8090](http://localhost:8090) dan backend API di [http://localhost:8091](http://localhost:8091). Halaman Lakehouse membaca `storage_manifest.json` melalui backend untuk menampilkan status Raw, Bronze, Silver, Gold, Quarantine, Metrics, Reports, dan Iceberg warehouse beserta jumlah file, path lokal, dan prefix S3.

Portal tidak mengasumsikan asal data. Data dapat berasal dari generator, unggahan, atau sumber lain; portal hanya membaca artefak yang benar-benar tersedia. Nilai konfigurasi seperti target prodi, target periode, atau target baris hanya ditampilkan sebagai konfigurasi, bukan sebagai hasil proses.

Sumber kebenaran status sistem dibuat oleh:

```powershell
python src/status/system_truth_status.py
```

Output:

- `outputs/reports/system_truth_status.json`
- `outputs/reports/system_truth_status.csv`

Status yang dipakai portal:

- `missing` atau `not_started`: proses belum menghasilkan artefak.
- `manual_input_required`: instrumen ada, tetapi input penilaian belum tersedia.
- `configured`: komponen dikonfigurasi, belum tentu berjalan.
- `ready` atau `validated`: artefak tersedia dan dapat dipakai sebagai hasil.
- `fallback`: nilai berasal dari konfigurasi, bukan hasil proses.
- `unreachable` atau `configured_unreachable`: layanan tidak dapat dijangkau.
- `skipped`: proses seperti upload MinIO tidak dijalankan.

Warna indikator mengikuti status aktual:

- Hijau hanya untuk `ready`, `validated`, `uploaded`, `created`, atau `completed`.
- Kuning/abu-abu untuk konfigurasi, mapping, skipped, missing, atau not started.
- Merah untuk `failed`, `unreachable`, `configured_unreachable`, atau `inconsistent`.

Alur validasi bertahap:

1. Fresh clone: portal dapat dibuka, tetapi kartu hasil menampilkan `missing` atau `not_started`.
2. Data tersedia: sumber PDF/CSV/Excel dapat `ready`, tetapi Quality Gate, Bronze, Silver, Gold, dan metrik tetap belum tersedia sampai script terkait dijalankan.
3. Quality Gate: `valid_rows`, `rejected_rows`, dan `dropout_rate` muncul hanya dari `data/quarantine/logs/quality_gate_summary.json`.
4. ETL: status Bronze, Silver, dan Gold membaca artefak layer aktual.
5. Metrics: latency, freshness, dropout, quality score, dan rekonsiliasi membaca file di `outputs/metrics`.
6. UAT: nilai UAT muncul hanya jika respons dan ringkasan UAT tersedia.
7. Dashboard validation: Superset tidak dinyatakan berhasil jika endpoint/API tidak dapat dijangkau.
8. Storage validation: MinIO upload hanya `uploaded` jika upload benar-benar dijalankan dan berhasil; jika upload off, status tetap `skipped` atau `mapped`.
9. Service validation: status service mengikuti health endpoint/TCP check aktual.

Matriks UAT dibuat dengan:

```powershell
python src/metrics/generate_uat.py
```

Output UAT:

- `outputs/uat/uat_template.csv`
- `outputs/uat/uat_dummy_response.csv`
- `outputs/uat/uat_score_summary.json`
- `outputs/uat/uat_matrix_summary.csv`
- `outputs/uat/uat_matrix_summary.json`

Data UAT adalah simulasi final yang eksplisit untuk kebutuhan laporan, dengan rata-rata `4,84`, persentase `96,80%`, dan kategori `Sangat baik`. Istilah visual dashboard mengikuti implementasi Superset: Big Number, Bar Chart, Pie Chart, Line Chart, dan Table.

---

## 🔐 Server Deployment (SSH Hardening)

Jika sistem Lakehouse ini akan dide-deploy ke lingkungan **Production (Cloud/VPS)**, direkomendasikan mengadopsi akses berbasis **SSH Key** dan menghindari penggunaan password biasa (SSH Hardening) guna menjaga keamanan infrastruktur Big Data.

**Prosedur Standar Migrasi Cloud:**

1. **Generate SSH Keypairs (Client):**
```bash
ssh-keygen -t ed25519 -C "data_engineer@namakampus.ac.id" -f ~/.ssh/id_ed25519_lakehouse
```

2. **Distribusi Public Key ke Server (Remote):**
```bash
ssh-copy-id -i ~/.ssh/id_ed25519_lakehouse.pub deploy_user@IP_SERVER
```

3. **Deploy Source Code via Rsync:**
Pastikan folder *cache* dan direktori sementara di-exclude dari transfer:
```bash
rsync -avz --exclude 'data/generated' --exclude '.venv' --exclude '__pycache__' -e "ssh -i ~/.ssh/id_ed25519_lakehouse" ./ deploy_user@IP_SERVER:/opt/lakehouse/
```

4. **Inisialisasi Remote Container:**
```bash
ssh -i ~/.ssh/id_ed25519_lakehouse deploy_user@IP_SERVER "cd /opt/lakehouse && docker-compose up -d"
```
*Selalu sesuaikan file `.env` di tahap produksi, terutama kredensial MinIO dan Postgres, guna mencegah potensi eksploitasi pada storage layer.*
