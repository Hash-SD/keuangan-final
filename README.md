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
docker exec keuangan-trino trino --catalog iceberg --schema gold --execute "SELECT SUM(nominal_piutang_rp), COUNT(*) FROM fact_piutang_ukt_prodi f JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key WHERE o.nama_prodi = 'Sains Data'"
```
**Output Diharapkan:**
```text
"31250000","15"
```
*(Angka di atas harus selaras dengan ketentuan Nilai Kontrol Uji Coba).*

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
