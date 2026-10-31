# Evidence index

Audit timestamp: `2026-09-25T04:21:17.969682+00:00`

| Subsection | Bukti | Lokasi | Status |
|---|---|---|---|
| 4.1.1 | Inventaris workbook dan struktur sheet | `tables/tab_411_*.csv` | VERIFIED jika sumber aktif terbaca |
| 4.1.3 | Schema dan lineage Gold | `tables/tab_413_*.csv` | berdasarkan fact_anggaran aktual |
| 4.2.2 | Manifest Bronze/Silver | `00_manifest/artifact_manifest.csv` | berdasarkan file aktual |
| 4.2.3 | Manifest Gold dan grafik | `00_manifest/artifact_manifest.csv`, `figures/` | berdasarkan file aktual |
| 4.3.1 | Rekonsiliasi dan validation report | `outputs/reports/` dan manifest | perlu dibedakan historis/baru |
| 4.3.3 | UAT | `screenshot_requests.md` | BELUM TERSEDIA bila respons tidak ada |

## Grafik yang dibuat

- `outputs/bab4_evidence/figures/fig_411_sel_per_workbook.png`
- `outputs/bab4_evidence/figures/fig_413_kelengkapan_lineage.png`
