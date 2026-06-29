from __future__ import annotations

import pandas as pd

from src.gold.fact_anggaran import build_fact_anggaran


def test_fact_anggaran_allocates_multi_iku_without_double_count():
    silver = pd.DataFrame(
        [
            {
                "item_id": "i1",
                "tahun": "2025",
                "periode": None,
                "prodi": "Sains Data",
                "kegiatan": "Kuliah Tamu",
                "akun": "522151 - Belanja Jasa Profesi",
                "iku": "IK 1.1; IK 2.1",
                "nomenklatur_path": "A > B",
                "qty": 1,
                "harga_satuan": 100,
                "jumlah": 100,
                "mapping_status": "exact_match",
                "data_quality_flag": "OK",
                "source_file": "rab.xlsx",
                "source_sheet": "RAB",
                "source_row": 10,
            }
        ]
    )

    fact = build_fact_anggaran(silver)

    assert len(fact) == 2
    assert set(fact["iku"]) == {"IK 1.1", "IK 2.1"}
    assert fact["allocation_weight"].tolist() == [0.5, 0.5]
    assert fact["jumlah_weighted_iku"].sum() == 100
