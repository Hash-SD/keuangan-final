from __future__ import annotations

import pandas as pd

from src.transformations import silver_clean


def test_silver_combined_output_replaces_only_current_session(tmp_path, monkeypatch):
    monkeypatch.setattr(silver_clean, "GENERATED_DIR", tmp_path / "generated")

    silver_clean._write_session_and_combined(
        pd.DataFrame(
            [
                {"dataset_session_id": "session-2025", "tahun_akademik": "2025/2026", "nominal_piutang_rp": 1000},
                {"dataset_session_id": "session-2026", "tahun_akademik": "2026/2027", "nominal_piutang_rp": 2000},
            ]
        ),
        "fact_piutang_ukt_prodi.csv",
        "session-2026",
    )
    silver_clean._write_session_and_combined(
        pd.DataFrame(
            [
                {"dataset_session_id": "session-2027", "tahun_akademik": "2027/2028", "nominal_piutang_rp": 3000},
            ]
        ),
        "fact_piutang_ukt_prodi.csv",
        "session-2027",
    )
    silver_clean._write_session_and_combined(
        pd.DataFrame(
            [
                {"dataset_session_id": "session-2026", "tahun_akademik": "2026/2027", "nominal_piutang_rp": 2500},
            ]
        ),
        "fact_piutang_ukt_prodi.csv",
        "session-2026",
    )

    combined = pd.read_csv(tmp_path / "generated" / "silver" / "fact_piutang_ukt_prodi.csv")
    by_session = dict(zip(combined["dataset_session_id"], combined["nominal_piutang_rp"], strict=True))

    assert by_session == {"session-2025": 1000, "session-2027": 3000, "session-2026": 2500}
    assert (tmp_path / "generated" / "silver" / "session-2026" / "fact_piutang_ukt_prodi.csv").exists()
