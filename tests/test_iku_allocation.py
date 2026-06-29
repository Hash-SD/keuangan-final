from __future__ import annotations

import pandas as pd

from src.gold.fact_anggaran import build_fact_anggaran


def test_iku_allocation_equal_split_for_three_iku():
    fact = build_fact_anggaran(
        pd.DataFrame(
            [
                {
                    "item_id": "item-1",
                    "tahun": "2025",
                    "prodi": "Sains Data",
                    "kegiatan": "PKS",
                    "akun": "521211",
                    "iku": "IK 1.1; IK 1.2; IK 1.3",
                    "jumlah": 300,
                    "mapping_status": "parsed",
                    "data_quality_flag": "OK",
                }
            ]
        )
    )

    assert len(fact) == 3
    assert round(fact["allocation_weight"].sum(), 6) == 1
    assert round(fact["jumlah_weighted_iku"].sum(), 6) == 300
