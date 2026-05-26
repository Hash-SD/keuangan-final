from __future__ import annotations

import random
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import GENERATED_DIR, RAW_DIR, ensure_parent


SAINS_DATA_NOMINALS = [
    2_500_000,
    2_500_000,
    2_250_000,
    2_250_000,
    2_000_000,
    2_000_000,
    2_000_000,
    2_000_000,
    1_750_000,
    1_750_000,
    1_750_000,
    1_750_000,
    1_500_000,
    1_500_000,
    3_750_000,
]


def build_piutang_rows(seed: int = 20260526) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    kualitas_options = [
        ("Lancar", 0.5),
        ("Kurang Lancar", 10.0),
        ("Diragukan", 50.0),
        ("Macet", 100.0),
    ]

    for idx, nominal in enumerate(SAINS_DATA_NOMINALS, start=1):
        kualitas, penyisihan = kualitas_options[idx % len(kualitas_options)]
        rows.append(
            {
                "nim": f"SD2024{idx:04d}",
                "nama_debitur": f"Mahasiswa Dummy Sains {idx:02d}",
                "fakultas": "Fakultas Sains",
                "prodi": "Sains Data",
                "semester": "Ganjil" if idx % 2 else "Genap",
                "tahun_akademik": "2023/2024",
                "umur_tunggakan": rng.randint(1, 6),
                "kualitas": kualitas,
                "persentase_penyisihan": penyisihan,
                "nominal_piutang_rp": nominal,
            }
        )

    prodi_options = ["Teknik Informatika", "Teknik Elektro", "Farmasi", "Matematika", "Arsitektur"]
    fakultas_by_prodi = {
        "Teknik Informatika": "Fakultas Teknologi Industri",
        "Teknik Elektro": "Fakultas Teknologi Industri",
        "Farmasi": "Fakultas Sains",
        "Matematika": "Fakultas Sains",
        "Arsitektur": "Fakultas Infrastruktur",
    }
    for idx in range(16, 804):
        prodi = rng.choice(prodi_options)
        kualitas, penyisihan = rng.choice(kualitas_options)
        rows.append(
            {
                "nim": f"DM2024{idx:04d}",
                "nama_debitur": f"Mahasiswa Dummy {idx:03d}",
                "fakultas": fakultas_by_prodi[prodi],
                "prodi": prodi,
                "semester": rng.choice(["Ganjil", "Genap"]),
                "tahun_akademik": rng.choice(["2022/2023", "2023/2024"]),
                "umur_tunggakan": rng.randint(1, 8),
                "kualitas": kualitas,
                "persentase_penyisihan": penyisihan,
                "nominal_piutang_rp": rng.choice([750_000, 1_000_000, 1_250_000, 1_500_000, 2_000_000]),
            }
        )
    return pd.DataFrame(rows)


def _rupiah(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def write_pdf(path: Path | None = None) -> Path:
    path = path or (RAW_DIR / "pdf" / "ITERA_LKTA2024Audited.pdf")
    ensure_parent(path)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    df = build_piutang_rows()
    df.to_csv(GENERATED_DIR / "dummy_piutang_master.csv", index=False)

    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Laporan Keuangan Tahunan Audited 2024 - Data Dummy", styles["Title"]),
        Paragraph("Laporan Realisasi Anggaran", styles["Heading2"]),
        Paragraph("Pendapatan Penerimaan Negara Bukan Pajak: Rp170.036.699.916", styles["Normal"]),
        Paragraph("Catatan Hasil Reviu Piutang", styles["Heading2"]),
        Paragraph("Total piutang mahasiswa pada tabel reviu piutang: Rp4.507.694.500", styles["Normal"]),
        Paragraph("Total mahasiswa penunggak: 803", styles["Normal"]),
        Spacer(1, 10),
        Paragraph("Tabel 1 Kriteria Piutang", styles["Heading2"]),
    ]

    kualitas_table = Table(
        [
            ["Kualitas", "Kriteria", "Persentase Penyisihan"],
            ["Lancar", "Tunggakan sampai 1 semester", "0.5%"],
            ["Kurang Lancar", "Tunggakan 2 sampai 3 semester", "10%"],
            ["Diragukan", "Tunggakan 4 sampai 5 semester", "50%"],
            ["Macet", "Tunggakan lebih dari 5 semester", "100%"],
        ],
        hAlign="LEFT",
    )
    kualitas_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)]))
    story.extend([kualitas_table, PageBreak(), Paragraph("Lampiran Debitur Piutang UKT Mahasiswa", styles["Heading2"])])

    headers = ["nim", "nama_debitur", "fakultas", "prodi", "semester", "tahun_akademik", "umur", "kualitas", "penyisihan", "nominal"]
    table_data = [headers]
    for row in df.itertuples(index=False):
        table_data.append(
            [
                row.nim,
                row.nama_debitur,
                row.fakultas,
                row.prodi,
                row.semester,
                row.tahun_akademik,
                str(row.umur_tunggakan),
                row.kualitas,
                str(row.persentase_penyisihan),
                _rupiah(int(row.nominal_piutang_rp)),
            ]
        )
    table = Table(table_data, repeatRows=1, colWidths=[58, 105, 112, 92, 46, 62, 28, 72, 48, 62])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.2, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    doc.title = "ITERA LKTA 2024 Audited Dummy"
    doc.author = "Synthetic Generator"
    doc.build(story)
    return path


if __name__ == "__main__":
    started = datetime.now()
    output = write_pdf()
    print(f"{output} ({(datetime.now() - started).total_seconds():.2f}s)")
