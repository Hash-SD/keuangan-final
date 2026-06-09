from pathlib import Path


def test_gold_view_sql_exposes_dashboard_filter_columns():
    sql = (Path(__file__).resolve().parents[1] / "src" / "sql" / "superset_datasets.sql").read_text(encoding="utf-8")

    for column in [
        "tahun_akademik",
        "tahun_anggaran",
        "semester",
        "nama_prodi",
        "nama_fakultas",
        "kualitas",
        "nominal_piutang_rp",
        "jumlah_mhs_penunggak",
        "nim",
        "nama_debitur",
    ]:
        assert column in sql
