from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import OUTPUTS_DIR, ensure_parent


QUESTIONS = [
    ("Navigation Facility", "Apakah filter prodi, semester, dan status piutang mudah digunakan?"),
    ("Clarity of Visualization", "Apakah visual Big Number, Bar Chart, Gauge Chart, dan tabel mudah dibaca?"),
    ("Data Relevance", "Apakah informasi piutang sesuai dengan kebutuhan pemantauan prodi?"),
    ("Data Consistency", "Apakah rincian mahasiswa, status kualitas, dan nominal tampil konsisten tanpa duplikasi?"),
    ("Usefulness in Decision", "Apakah informasi piutang macet membantu prioritas tindak lanjut?"),
]


def main() -> None:
    uat_dir = OUTPUTS_DIR / "uat"
    template = pd.DataFrame([{"indikator": i, "pertanyaan": q, "skala_min": 1, "skala_max": 5} for i, q in QUESTIONS])
    ensure_parent(uat_dir / "uat_template.csv")
    template.to_csv(uat_dir / "uat_template.csv", index=False)
    roles = ["Kaprodi", "Dosen Wali", "Staf Administrasi"]
    responses = []
    for role in roles:
        for idx, (indicator, question) in enumerate(QUESTIONS):
            responses.append({"responden": role, "indikator": indicator, "pertanyaan": question, "skor": [5, 4, 5, 4, 5][idx]})
    response_df = pd.DataFrame(responses)
    response_df.to_csv(uat_dir / "uat_dummy_response.csv", index=False)
    average = float(response_df["skor"].mean())
    category = "Sangat baik" if average >= 4.21 else "Baik" if average >= 3.41 else "Cukup"
    write_json(uat_dir / "uat_score_summary.json", {"average_score": round(average, 2), "category": category, "response_count": len(response_df)})


if __name__ == "__main__":
    main()

