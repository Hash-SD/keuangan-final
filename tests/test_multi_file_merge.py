from __future__ import annotations

import pandas as pd


def test_multi_file_merge_keeps_source_lineage_and_periods():
    jan = pd.DataFrame([{"item_id": "jan-1", "periode": "Jan-Jun", "source_file": "jan.xlsx", "jumlah": 10}])
    jul = pd.DataFrame([{"item_id": "jul-1", "periode": "Jul-Des", "source_file": "jul.xlsx", "jumlah": 20}])

    merged = pd.concat([jan, jul], ignore_index=True)

    assert set(merged["periode"]) == {"Jan-Jun", "Jul-Des"}
    assert set(merged["source_file"]) == {"jan.xlsx", "jul.xlsx"}
    assert merged["jumlah"].sum() == 30
    assert merged["item_id"].is_unique
