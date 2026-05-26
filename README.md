# Data Lakehouse Keuangan Prodi

Implementasi lokal Data Lakehouse berbasis Medallion Architecture untuk data keuangan perguruan tinggi. Proyek ini mengikuti rencana kerja di `end_to_end_plan_data_lakehouse_mcp_skills.md` dan dikerjakan secara checkpoint-based.

## Target

- Generate data dummy PDF, CSV, dan Excel.
- Validasi quality gate dan quarantine data rusak.
- Bangun Bronze, Silver, dan Gold layer.
- Bentuk star schema untuk analisis piutang UKT Prodi Sains Data.
- Hubungkan Gold layer ke Trino dan Superset.
- Hitung metrik evaluasi dan siapkan UAT dashboard.

## Nilai Kontrol

| Kontrol | Target |
|---|---:|
| Total tunggakan UKT Prodi Sains Data | 31250000 |
| Jumlah mahasiswa penunggak Sains Data | 15 |
| Total pagu RAB Sains Data | 150000000 |

## Quick Start

```powershell
Copy-Item .env.example .env
make generate-data
make run-quality-gate
make run-bronze
make run-silver
make run-gold
make run-metrics
make test
```

Stack Docker akan disiapkan pada checkpoint berikutnya. Target akhirnya:

```powershell
make up
make full-run
```

## Checkpoint

Progress tersimpan di `docs/checkpoints/`. Mulai dari `CHECKPOINT-00-setup.md` dan lanjut berurutan sampai `CHECKPOINT-09-final-run.md`.

