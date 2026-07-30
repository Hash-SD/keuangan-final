# Bab IV Evidence Summary

Audit timestamp: `2026-07-30T10:15:16.410660+00:00`

## 4.1.1 Analisis data sumber
- Bukti inventaris workbook, hash, sheet, dimensi, formula, dan metadata tersedia pada `tables/tab_411_*`.

## 4.1.3 Model Gold dan lineage
- fact_anggaran: 607 baris dan 33 kolom.
- Duplikasi grain terdeteksi: 0 baris berdasarkan kolom grain yang tersedia.
- Total `jumlah`: 1494181466.0; total `jumlah_weighted_iku`: 517361656.0.

## 4.2 Implementasi
- Manifest artefak menunjukkan file aktual, ukuran, hash, schema, jumlah baris bila dapat dibaca, dan status pemeriksaan.

## 4.3 Pengujian
- Validasi baru dibatasi pada audit read-only ini dan laporan repository yang dapat ditelusuri.
- UAT: BELUM TERSEDIA kecuali instrumen dan respons pengguna ditemukan.

## Keterbatasan
- Lihat `00_manifest/limitations.md`.
