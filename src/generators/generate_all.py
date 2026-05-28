from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.generators.generate_csv_transactions import write_transactions
from src.generators.generate_excel_rab import write_rab
from src.generators.generate_pdf_audited import write_pdf
from src.generators.master_biaya import write_master_biaya


def main() -> None:
    outputs = [*write_master_biaya(), write_pdf(), *write_transactions(), write_rab()]
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
