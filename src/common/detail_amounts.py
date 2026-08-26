from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from src.common.money import canonical_currency, normalize_money


def numeric_or_none(value: object) -> float | None:
    """Return a scalar numeric value without converting missing values to zero."""

    return normalize_money(value)


def _display_number(value: float | None) -> float | int | None:
    if value is None:
        return None
    return canonical_currency(value)


def normalize_detail_amounts(record: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize canonical detail amounts while keeping values numeric.

    A line item with no quantity or unit price represents one item whose unit
    price is the recorded total amount. This rule is applied in Silver and
    repeated at the Gold boundary as a defensive contract safeguard.
    """

    normalized = dict(record)
    amount = canonical_currency(normalized.get("jumlah"))
    quantity = numeric_or_none(normalized.get("qty"))
    unit_price = canonical_currency(normalized.get("harga_satuan"))
    quantity_missing = quantity in (None, 0)
    unit_price_missing = unit_price in (None, 0)

    if amount is None and not quantity_missing and not unit_price_missing:
        amount = quantity * unit_price

    if amount is not None and (quantity_missing or unit_price_missing):
        quantity = 1.0
        unit_price = amount
    else:
        if quantity_missing:
            quantity = 1.0
        if unit_price_missing and amount is not None:
            unit_price = amount / quantity if quantity else amount

    normalized["qty"] = _display_number(quantity)
    normalized["harga_satuan"] = _display_number(unit_price)
    if amount is not None:
        normalized["jumlah"] = _display_number(amount)
    return normalized


def normalize_detail_amount_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a new frame with the detail amount contract applied."""

    if frame.empty:
        return frame.copy()
    rows = [normalize_detail_amounts(row) for row in frame.to_dict(orient="records")]
    normalized = pd.DataFrame(rows, index=frame.index)
    columns = list(dict.fromkeys([*frame.columns, "qty", "harga_satuan", "jumlah"]))
    return normalized.reindex(columns=columns)
