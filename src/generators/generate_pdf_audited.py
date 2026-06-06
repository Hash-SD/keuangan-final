from __future__ import annotations

import random
import sys
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import GENERATED_DIR, RAW_DIR, ensure_parent
from src.common.runtime_config import get_runtime_config
from src.common.runtime_paths import raw_pdf_path

def load_prodi_data() -> dict:
    json_data = """{
  "Fisika": {"fakultas": "Fakultas Sains", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 17500000},
  "Matematika": {"fakultas": "Fakultas Sains", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 8849000], "spi": 25000000},
  "Biologi": {"fakultas": "Fakultas Sains", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 24000000},
  "Kimia": {"fakultas": "Fakultas Sains", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 17500000},
  "Farmasi": {"fakultas": "Fakultas Sains", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 30000000},
  "Sains Data": {"fakultas": "Fakultas Sains", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 30000000},
  "Sains Aktuaria": {"fakultas": "Fakultas Sains", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 8849000], "spi": 30000000},
  "Sains Lingkungan Kelautan": {"fakultas": "Fakultas Sains", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 17500000},
  "Sains Atmosfir dan Keplanetan": {"fakultas": "Fakultas Sains", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 21500000},
  "Teknik Elektro": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 30000000},
  "Teknik Fisika": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 17500000},
  "Teknik Informatika": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9000000], "spi": 30000000},
  "Teknik Geologi": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 22500000},
  "Teknik Geofisika": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 26000000},
  "Teknik Mesin": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 26500000},
  "Teknik Kimia": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9371000], "spi": 28500000},
  "Teknik Material": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 21500000},
  "Teknik Sistem Energi": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 17500000},
  "Teknik Industri": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9371000], "spi": 30000000},
  "Teknik Telekomunikasi": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9371000], "spi": 28500000},
  "Teknik Pertambangan": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 30000000},
  "Teknik Biosistem": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 17500000},
  "Teknik Biomedis": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 27500000},
  "Teknologi Pangan": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9344000], "spi": 30000000},
  "Teknologi Industri Pertanian": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9371000], "spi": 28500000},
  "Rekayasa Kehutanan": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9344000], "spi": 17500000},
  "Rekayasa Kosmetik": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 21500000},
  "Rekayasa Minyak dan Gas": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 27500000},
  "Rekayasa Instrumentasi dan Automasi": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 22500000},
  "Rekayasa Keolahragaan": {"fakultas": "Fakultas Teknologi Industri", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 20000000},
  "Teknik Geomatika": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 26000000},
  "Perencanaan Wilayah dan Kota": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 30000000},
  "Teknik Sipil": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 30000000},
  "Arsitektur": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 27500000},
  "Teknik Lingkungan": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 28500000},
  "Teknik Kelautan": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 24000000},
  "Desain Komunikasi Visual": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 8098000], "spi": 30000000},
  "Arsitektur Lanskap": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 24000000},
  "Teknik Perkeretaapian": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 26500000},
  "Rekayasa Tata Kelola Air Terpadu": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 21500000},
  "Pariwisata": {"fakultas": "Fakultas Teknologi Infrastruktur & Kewilayahan", "ukts": [500000, 1000000, 2000000, 3500000, 5000000, 6500000, 8000000, 9500000], "spi": 25000000}
}"""
    return json.loads(json_data)

def _target_nominals(config, prodi_info: dict, count: int, rng: random.Random) -> list[int]:
    if config.target_prodi == "Sains Data" and config.target_total_piutang is None and count == 15:
        return [
            2_500_000,
            2_500_000,
            2_250_000,
            2_250_000,
            2_000_000,
            2_000_000,
            2_000_000,
            2_000_000,
            2_000_000,
            2_000_000,
            1_750_000,
            1_750_000,
            1_750_000,
            2_250_000,
            2_250_000,
        ]
    if config.target_total_piutang is not None and count > 0:
        base = (config.target_total_piutang // count // 50_000) * 50_000
        nominals = [base for _ in range(count)]
        nominals[-1] += config.target_total_piutang - sum(nominals)
        return nominals
    ukts = prodi_info.get("ukts", [2_500_000])
    return [(rng.choice(ukts) // 50_000) * 50_000 for _ in range(count)]


def build_piutang_rows(seed: int = 99999999) -> pd.DataFrame:
    config = get_runtime_config()
    rng = random.Random(config.dummy_seed if seed == 99999999 else seed)
    rows = []
    kualitas_options = [
        ("Lancar", 0.5),
        ("Kurang Lancar", 10.0),
        ("Diragukan", 50.0),
        ("Macet", 100.0),
    ]

    prodi_data = load_prodi_data()
    prodi_data.setdefault(
        config.target_prodi,
        {"fakultas": config.target_fakultas, "ukts": [500_000, 1_000_000, 2_000_000, 3_500_000, 5_000_000, 6_500_000, 8_000_000, 9_500_000], "spi": 30_000_000},
    )
    all_prodis = [prodi for prodi in prodi_data.keys() if prodi != config.target_prodi]
    target_count = config.target_jumlah_penunggak or 15
    target_nominals = _target_nominals(config, prodi_data[config.target_prodi], target_count, rng)

    for idx in range(1, target_count + 1):
        kualitas, penyisihan = kualitas_options[idx % len(kualitas_options)]
        prodi = config.target_prodi
        golongan = rng.randint(0, 7)
        base_ukt = prodi_data[prodi]["ukts"][golongan]
        nominal = target_nominals[idx - 1]
        prodi_slug = "".join(part[0] for part in prodi.split() if part).upper()[:3] or "PRD"

        rows.append(
            {
                "nim": f"{prodi_slug}2024{idx:04d}",
                "nama_debitur": f"Mahasiswa Dummy {prodi} {idx:02d}",
                "fakultas": prodi_data.get(prodi, {}).get("fakultas", config.target_fakultas),
                "prodi": prodi,
                "semester": "Ganjil" if idx % 2 else "Genap",
                "tahun_akademik": config.target_tahun_akademik,
                "umur_tunggakan": rng.randint(1, 6),
                "kualitas": kualitas,
                "persentase_penyisihan": penyisihan,
                "nominal_piutang_rp": nominal,
                "base_ukt": base_ukt, # store for later use by transactions
                "golongan_ukt": f"Gol. {golongan + 1}",
                "spi": prodi_data.get(prodi, {}).get("spi", 30_000_000)
            }
        )

    for idx in range(target_count + 1, 804):
        prodi = rng.choice(all_prodis)
        kualitas, penyisihan = rng.choice(kualitas_options)
        
        golongan = rng.randint(0, 7)
        base_ukt = prodi_data[prodi]["ukts"][golongan]
        
        # Nominal piutang is a random amount up to max UKT to make it realistic
        min_nominal = min(500_000, base_ukt)
        nominal_piutang = rng.randint(min_nominal, base_ukt)
        nominal_piutang = (nominal_piutang // 50000) * 50000

        umur_tunggakan = rng.randint(1, 8)
        
        rows.append(
            {
                "nim": f"DM2024{idx:04d}",
                "nama_debitur": f"Mahasiswa Dummy {idx:03d}",
                "fakultas": prodi_data[prodi]["fakultas"],
                "prodi": prodi,
                "semester": rng.choice(["Ganjil", "Genap"]),
                "tahun_akademik": rng.choice([config.target_tahun_akademik, "2022/2023"]),
                "umur_tunggakan": umur_tunggakan,
                "kualitas": kualitas,
                "persentase_penyisihan": penyisihan,
                "nominal_piutang_rp": nominal_piutang,
                "base_ukt": base_ukt,
                "golongan_ukt": f"Gol. {golongan + 1}",
                "spi": prodi_data[prodi]["spi"]
            }
        )
    return pd.DataFrame(rows)


def _rupiah(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def write_pdf(path: Path | None = None) -> Path:
    config = get_runtime_config()
    path = path or raw_pdf_path()
    ensure_parent(path)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    df = build_piutang_rows()
    df.to_csv(GENERATED_DIR / "dummy_piutang_master.csv", index=False)

    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Laporan Keuangan Tahunan Audited {config.target_tahun_anggaran} - Data Dummy", styles["Title"]),
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
    doc.title = f"ITERA LKTA {config.target_tahun_anggaran} Audited Dummy"
    doc.author = "Synthetic Generator"
    doc.build(story)
    return path


if __name__ == "__main__":
    started = datetime.now()
    output = write_pdf()
    print(f"{output} ({(datetime.now() - started).total_seconds():.2f}s)")
