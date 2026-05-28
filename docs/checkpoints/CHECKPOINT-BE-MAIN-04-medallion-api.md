# CHECKPOINT-BE-MAIN-04: Medallion API

## Tujuan
Memastikan API Bronze/Silver/Gold sesuai Medallion Architecture pada `main.pdf`.

## File Dibaca
- src/transformations/bronze_ingest.py
- src/transformations/silver_clean.py
- src/transformations/gold_star_schema.py
- portal_backend/services/lakehouse.py

## Dokumentasi Context7 yang Dibaca
- Python/cpython: pathlib dan csv.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- portal_backend/services/lakehouse.py
- portal_backend/services/pipeline.py

## Implementasi
Endpoint yang dipakai:
```text
POST /api/pipeline/bronze
POST /api/pipeline/silver
POST /api/pipeline/gold
GET  /api/lakehouse/summary
```

Activity action diselaraskan:
- `extract_bronze`
- `clean_silver`
- `load_gold_schema`

## Command yang Dijalankan
```bash
python src/transformations/bronze_ingest.py
python src/transformations/silver_clean.py
python src/transformations/gold_star_schema.py
Invoke-RestMethod -Uri http://localhost:8091/api/lakehouse/summary
```

## Hasil Validasi
Bronze, Silver, dan Gold berstatus ready. Gold valid terhadap reconcile control total.

## Masalah / Risiko
Bronze metadata dari script pipeline dapat memuat path lokal untuk kebutuhan internal, tetapi API frontend tetap mengembalikan path relatif pada endpoint status sumber data.

## Keputusan Teknis
Lakehouse summary diberi deskripsi layer sesuai proposal.

## Langkah Berikutnya
Validasi metrics API.

## Status
Selesai
