from pathlib import Path


def test_gold_sql_exposes_excel_dashboard_filter_columns():
    sql = (Path(__file__).resolve().parents[1] / "src" / "sql" / "create_gold_tables.sql").read_text(encoding="utf-8")

    for column in [
        "tahun",
        "periode",
        "prodi",
        "fakultas",
        "kode_iku",
        "nama_iku",
        "kegiatan",
        "kode_akun",
        "nama_akun",
        "data_quality_flag",
    ]:
        assert column in sql
