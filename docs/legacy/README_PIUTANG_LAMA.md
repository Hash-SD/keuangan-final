# Legacy Piutang UKT Pipeline

Dokumen ini mencatat domain lama repository sebelum redesign Excel Lakehouse.

Domain lama:

- PDF audited
- CSV transaksi
- Piutang UKT
- `fact_piutang_ukt_prodi`
- Dashboard piutang UKT
- Dummy data generator sebagai pipeline utama

Status pada branch `feature/excel-lakehouse-v2-final`:

- Domain lama tidak lagi menjadi default pipeline.
- Modul lama masih ada sebagai legacy compatibility guard sampai cleanup agresif terpisah.
- Entry point baru adalah pipeline Excel-only berbasis RAB/RPD/IKU/Nomenklatur dan `fact_anggaran`.
