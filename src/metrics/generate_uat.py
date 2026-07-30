from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import OUTPUTS_DIR, ensure_parent
from src.common.runtime_config import configured_batch_id
from src.common.time_utils import utc_now_iso


DASHBOARD_QUESTIONS = [
    ("Navigation Facility", "Apakah filter tahun, prodi, IKU, kegiatan, dan akun pada dashboard mudah digunakan?"),
    ("Clarity of Visualization", "Apakah visual KPI, bar chart, tabel detail, dan validasi rekap pada dashboard mudah dibaca?"),
    ("Data Relevance", "Apakah informasi anggaran RAB dan IKU pada dashboard sesuai kebutuhan pemantauan prodi?"),
    ("Data Consistency", "Apakah rincian kegiatan, akun, IKU, dan nominal pada dashboard tampil konsisten tanpa duplikasi?"),
    ("Usefulness in Decision", "Apakah informasi anggaran per IKU pada dashboard membantu prioritas perencanaan prodi?"),
]

UAT_RESPONDENT = {
    "nama": "Pak Tirta",
    "peran": "Kaprodi",
}

DASHBOARD_SCORES = {
    "Navigation Facility": 5,
    "Clarity of Visualization": 5,
    "Data Relevance": 5,
    "Data Consistency": 5,
    "Usefulness in Decision": 5,
}


def _category(score: float) -> str:
    if score >= 4.21:
        return "Sangat baik"
    if score >= 3.41:
        return "Baik"
    if score >= 2.61:
        return "Cukup"
    if score >= 1.81:
        return "Kurang"
    return "Sangat kurang"


def main() -> None:
    uat_dir = OUTPUTS_DIR / "uat"
    source = "evaluasi UAT dashboard Excel Lakehouse; diisi oleh Pak Tirta selaku Kaprodi"
    template = pd.DataFrame(
        [
            {
                "indikator": indicator,
                "pertanyaan": question,
                "skala_min": 1,
                "skala_max": 5,
                "cakupan_uji": "Dashboard analitik anggaran RAB/IKU",
                "visual_dashboard": "KPI, Bar Chart, Detail Table, Mapping Quality, Validasi Rekap",
                "sumber_penilaian": source,
            }
            for indicator, question in DASHBOARD_QUESTIONS
        ]
    )
    ensure_parent(uat_dir / "uat_template.csv")
    template.to_csv(uat_dir / "uat_template.csv", index=False)
    responses = []
    for indicator, question in DASHBOARD_QUESTIONS:
        responses.append(
            {
                "responden": UAT_RESPONDENT["nama"],
                "peran": UAT_RESPONDENT["peran"],
                "indikator": indicator,
                "pertanyaan": question,
                "skor": DASHBOARD_SCORES[indicator],
                "cakupan_uji": "Dashboard analitik anggaran RAB/IKU",
                "sumber_penilaian": source,
            }
        )
    response_df = pd.DataFrame(responses)
    response_df.to_csv(uat_dir / "uat_response.csv", index=False)
    matrix_rows = []
    for indicator, question in DASHBOARD_QUESTIONS:
        indicator_scores = response_df[response_df["indikator"] == indicator]["skor"]
        average = float(indicator_scores.mean())
        matrix_rows.append(
            {
                "indikator": indicator,
                "pertanyaan": question,
                "skor_rata_rata": round(average, 2),
                "persentase": round(average / 5 * 100, 2),
                "kategori": _category(average),
                "jumlah_responden": int(indicator_scores.count()),
                "responden": UAT_RESPONDENT["nama"],
                "peran_responden": UAT_RESPONDENT["peran"],
                "cakupan_uji": "Dashboard analitik anggaran RAB/IKU",
                "sumber_penilaian": source,
            }
        )
    matrix = pd.DataFrame(matrix_rows)
    matrix.to_csv(uat_dir / "uat_matrix_summary.csv", index=False)

    average = float(response_df["skor"].mean())
    summary = {
        "batch_id": configured_batch_id(),
        "average_score": round(average, 2),
        "percentage": round(average / 5 * 100, 2),
        "category": _category(average),
        "respondent_count": 1,
        "response_count": len(response_df),
        "respondents": [UAT_RESPONDENT],
        "scope": "Dashboard analitik anggaran RAB/IKU",
        "source": source,
        "generated_at": utc_now_iso(),
        "required_indicators": [indicator for indicator, _ in DASHBOARD_QUESTIONS],
        "dashboard_visual_terms": ["KPI", "Bar Chart", "Detail Table", "Mapping Quality", "Validasi Rekap"],
    }
    write_json(uat_dir / "uat_score_summary.json", summary)
    write_json(uat_dir / "uat_matrix_summary.json", {"batch_id": configured_batch_id(), "generated_at": utc_now_iso(), "items": matrix_rows, "summary": summary})


if __name__ == "__main__":
    main()
