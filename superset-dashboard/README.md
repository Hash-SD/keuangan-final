# superset-dashboard

Dashboard lokal bertema UI/UX portal SILARAS SD (`http://localhost:8090/`) yang
meniru tata letak dashboard Superset **"SILARAS SD - Dashboard Anggaran IKU"**.
Seluruh data chart ditarik **langsung dari REST API Superset** — tidak membaca
database secara langsung.

## Arsitektur

```
superset-dashboard/
├── public/            # Frontend (HTML/CSS/JS/ECharts) — disajikan juga oleh Vercel
│   ├── treemap-data.js # Agregasi treemap deterministik, dapat diuji tanpa browser
│   └── dashboard-presentation.js # Normalisasi judul, label kolom, dan format KPI
├── lib/_shared.py     # Logika Superset API: login, dashboard meta, chart data, cache
├── api/index.py       # Entrypoint WSGI/Flask (dipakai Vercel)
├── server.py          # Server lokal Flask (dev / Docker)
├── Dockerfile         # Image untuk Docker
├── docker-compose.yml # Service menumpang network lakehouse_net (bisa akses superset:8088)
├── vercel.json        # Adapter Vercel (static public/ + fungsi /api/*)
└── requirements.txt
```

Alur data: **Browser → Flask proxy (`/api/...`) → Superset REST API
(`/api/v1/chart/...`) → kembali sebagai JSON**. Kredensial Superset hanya ada di
server, tidak pernah diekspos ke browser.

## Fitur

- **Pilih dashboard** — daftar dashboard ditarik live dari Superset
  (`GET /api/v1/dashboard/`). Urutan & tipe chart dibangun dinamis dari
  `position_json` + params tiap chart.
- **Filter tahun** — Semua / 2023 / 2024 / 2025, memakai filter `tahun IN (...)`
  pada query Superset.
- **Refresh paksa** — tombol Refresh mengambil data terbaru dari Superset
  (melewati cache 60 detik; `force: true` di sisi Superset).
- **5 KPI** (Total Anggaran, Total Weighted IKU, Jumlah Item, IKU, Kegiatan),
  bar chart, treemap, donut, dan tabel (paginasi + pencarian).
- **Layout responsif** — konten analitik terpusat dalam kontainer maksimum 1.480 px,
  urutan chart mengikuti hierarki bisnis, judul memakai sentence case, dan treemap
  merangking grup sebelum menggabungkan overflow ke node `Lainnya`.
- **Presentasi ringkas** — kartu Total anggaran menjadi metrik utama, metrik jumlah
  tidak diberi prefix Rupiah, label kolom teknis diterjemahkan tanpa underscore, dan
  status rekonsiliasi tampil sebagai strip status yang mudah dipindai.
- **Treemap rapat** — feature card dan canvas treemap menggunakan jarak internal
  yang lebih pendek agar visual mengisi area kartu tanpa ruang kosong berlebihan.
- Dark mode mengikuti preferensi sistem (tema portal v2).

## Menjalankan lokal (dev)

```bash
cd superset-dashboard
pip install -r requirements.txt

# Superset berjalan di host pada port 8089 (admin/admin) → default lokal sudah benar
python server.py
# → http://localhost:8092/
```

Set variabel bila diperlukan:

```bash
SUPERSET_BASE_URL=http://localhost:8089
SUPERSET_USERNAME=admin
SUPERSET_PASSWORD=admin
```

## Menjalankan dengan Docker

Service ini menumpang network `lakehouse_net` dari `docker-compose.yml` utama
(keuangan-final) sehingga dapat menjangkau container Superset lewat hostname
`superset:8088`. Pastikan compose utama sudah `docker compose up -d`.

```bash
cd superset-dashboard
docker compose up -d --build
# → http://localhost:8092/
```

Tanpa network utama, set `SUPERSET_BASE_URL` ke instance Superset yang dapat
dijangkau container, misalnya:

```bash
SUPERSET_BASE_URL=http://host.docker.internal:8089 docker compose up -d
```

## Menjalankan di Vercel

Proyek ini siap deploy sebagai satu proyek Vercel (static `public/` + Python
serverless function di `api/`):

1. `vercel login` lalu `vercel` di folder ini (atau impor repo di dashboard
   Vercel, root directory = `superset-dashboard`).
2. Set environment variables di project Vercel:
   - `SUPERSET_BASE_URL` — mis. `https://superset.publikanda.com`
   - `SUPERSET_USERNAME`
   - `SUPERSET_PASSWORD`
3. Deploy. Static files disajikan dari `public/`; permintaan `/api/*` diteruskan
   ke fungsi serverless `api/index.py` (lihat `vercel.json`).

> Catatan: kredensial Superset disimpan sebagai env vars di Vercel, tidak di
> commit ke git.

## Akses dari Portal

Tombol **"Buka Dashboard Lokal (Mirror Superset)"** sudah tersedia di portal v2
(`portal/v2/index.html`, view Dashboard BI) → `http://localhost:8092/`.
