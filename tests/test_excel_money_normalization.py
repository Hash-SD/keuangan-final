from __future__ import annotations

from src.excel_ingestion.excel_cell_extractor import normalize_money
from src.common.detail_amounts import normalize_detail_amounts
from src.transformations.budget_cleaning import REVIEW_ACCOUNT_LABEL, clean_account_label, extract_valid_account


def test_normalize_money_handles_indonesian_thousand_commas():
    assert normalize_money("Rp 750,000") == 750000.0
    assert normalize_money("Rp 15,000,000") == 15000000.0
    assert normalize_money("1.250.000") == 1250000.0


def test_normalize_money_keeps_decimal_values():
    assert normalize_money("12,5") == 12.5
    assert normalize_money("12.5") == 12.5


def test_detail_amounts_normalizes_formatted_amount_before_fallback():
    normalized = normalize_detail_amounts(
        {"qty": None, "harga_satuan": None, "jumlah": "Rp 2.520.000"}
    )

    assert normalized["qty"] == 1
    assert normalized["harga_satuan"] == 2_520_000
    assert normalized["jumlah"] == 2_520_000


def test_detail_amounts_handles_comma_grouped_amount():
    normalized = normalize_detail_amounts(
        {"qty": None, "harga_satuan": None, "jumlah": "2,520,000"}
    )

    assert normalized["harga_satuan"] == 2_520_000
    assert normalized["jumlah"] == 2_520_000


def test_detail_amounts_uses_total_when_either_detail_field_is_missing():
    for record in (
        {"qty": 0, "harga_satuan": 50, "jumlah": 100},
        {"qty": 2, "harga_satuan": None, "jumlah": 100},
    ):
        normalized = normalize_detail_amounts(record)

        assert normalized["qty"] == 1
        assert normalized["harga_satuan"] == 100


def test_detail_amounts_calculates_missing_total_from_quantity_and_price():
    normalized = normalize_detail_amounts(
        {"qty": 2, "harga_satuan": "Rp 1.250.000", "jumlah": None}
    )

    assert normalized["qty"] == 2
    assert normalized["harga_satuan"] == 1_250_000
    assert normalized["jumlah"] == 2_500_000


def test_detail_amounts_removes_excel_binary_noise_from_currency_values():
    normalized = normalize_detail_amounts(
        {
            "qty": 20,
            "harga_satuan": 3_330_000.0000000005,
            "jumlah": 666_000.0000000001,
        }
    )

    assert normalized["harga_satuan"] == 3_330_000
    assert normalized["jumlah"] == 666_000


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
