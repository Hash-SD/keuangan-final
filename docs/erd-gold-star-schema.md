# ER Diagram Star Schema Gold — SILARAS SD

> Sumber kebenaran: FK live di Postgres `metastore` schema `gold`
> (4 FK: `fact_anggaran_org_key_fkey`, `fact_anggaran_kegiatan_key_fkey`,
> `fact_anggaran_akun_key_fkey`, `fact_anggaran_iku_key_fkey`) dan
> `src/sql/create_gold_tables.sql`.

## Cara melihat diagram relasi

1. **DBeaver** — double-click `gold.fact_anggaran` → tab *ER Diagram*, atau klik kanan schema `gold` → *View Diagram*.
2. **pgAdmin 4** — klik kanan schema `gold` → *ERD For the database*.
3. **Mermaid/draw.io** — copy blok `mermaid` di bawah ke <https://mermaid.live> atau draw.io (*Arrange → Insert → Advanced → Mermaid*).

## Diagram relasi

```mermaid
erDiagram
    dim_organisasi ||--o{ fact_anggaran : "org_key (FK)"
    dim_kegiatan ||--o{ fact_anggaran : "kegiatan_key (FK)"
    dim_akun ||--o{ fact_anggaran : "akun_key (FK)"
    dim_iku ||--o{ fact_anggaran : "iku_key (FK)"

    fact_anggaran {
        SERIAL fact_key PK
        TEXT item_id "identitas item"
        TEXT dataset_session_id "identitas sesi"
        TEXT run_id "identitas run"
        TEXT tahun
        INTEGER org_key FK
        INTEGER kegiatan_key FK
        INTEGER akun_key FK
        INTEGER iku_key FK
        TEXT uraian_detail
        DOUBLE qty
        DOUBLE harga_satuan
        DOUBLE jumlah
        DOUBLE allocation_weight
        DOUBLE jumlah_weighted_iku "SUM = Total Anggaran"
        TEXT row_type
        TIMESTAMPTZ created_at
    }

    dim_organisasi {
        INTEGER org_key PK
        TEXT prodi
        TEXT fakultas
    }

    dim_kegiatan {
        INTEGER kegiatan_key PK
        TEXT kegiatan
        TEXT cluster_kegiatan
        TEXT nomenklatur_path
    }

    dim_akun {
        INTEGER akun_key PK
        TEXT kode_akun
        TEXT nama_akun
        TEXT akun
        TEXT nama_akun_asli
    }

    dim_iku {
        INTEGER iku_key PK
        TEXT kode_iku UK
        TEXT iku
        TEXT nama_iku
    }
```

## Catatan

- View `gold.vw_fact_anggaran` adalah rekonstruksi flat (JOIN 4 dim) untuk
  Superset/portal — bukan tabel fisik, tidak muncul di ERD.
- View analitik: `vw_dashboard_iku_anggaran`, `vw_dashboard_mapping_quality`,
  `vw_dashboard_reconciliation` — agregasi di atas `vw_fact_anggaran`.
- Grain fact: satu item anggaran x satu alokasi IKU.
