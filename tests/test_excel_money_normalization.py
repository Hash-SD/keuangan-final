from __future__ import annotations

from src.excel_ingestion.excel_cell_extractor import normalize_money
from src.transformations.budget_cleaning import REVIEW_ACCOUNT_LABEL, clean_account_label, extract_valid_account


def test_normalize_money_handles_indonesian_thousand_commas():
    assert normalize_money("Rp 750,000") == 750000.0
    assert normalize_money("Rp 15,000,000") == 15000000.0
    assert normalize_money("1.250.000") == 1250000.0


def test_normalize_money_keeps_decimal_values():
    assert normalize_money("12,5") == 12.5
    assert normalize_money("12.5") == 12.5


def test_aggregate_or_price_like_account_codes_require_review():
    assert extract_valid_account("530000 - Uang Harian Perjalanan Dinas - ORG") == (None, None)

    code, name, label = clean_account_label(
        {
            "akun": "530000 - Uang Harian Perjalanan Dinas - ORG",
            "kode_akun": "530000",
            "nama_akun": "Uang Harian Perjalanan Dinas - ORG",
        }
    )

    assert code is None
    assert name is None
    assert label == REVIEW_ACCOUNT_LABEL


def test_real_item_level_account_code_stays_valid():
    assert extract_valid_account("521211 - Belanja Bahan") == ("521211", "Belanja Bahan")
