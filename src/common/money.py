from __future__ import annotations

import math
import re


def normalize_money(value: object) -> float | None:
    """Parse numeric and common Indonesian/US-formatted money values.

    The pipeline stores amounts as numbers, but source workbooks and API
    payloads can still contain values such as ``Rp 2.520.000`` or
    ``2,520,000``. Keeping this parser at a shared boundary makes the
    detail-amount contract identical in ingestion, Silver, and Gold.
    """

    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return number if math.isfinite(number) else None

    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"[^0-9,.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None

    if "," in text and "." in text:
        separators = [idx for idx, char in enumerate(text) if char in ",."]
        decimal_separator = text[separators[-1]] if len(text) - separators[-1] - 1 != 3 else None
        if decimal_separator:
            thousands_separator = "." if decimal_separator == "," else ","
            text = text.replace(thousands_separator, "").replace(decimal_separator, ".")
        else:
            text = text.replace(",", "").replace(".", "")
    elif "," in text:
        parts = text.split(",")
        if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
            text = "".join(parts)
        else:
            text = text.replace(",", ".")
    elif "." in text:
        parts = text.split(".")
        if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
            text = "".join(parts)

    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def canonical_currency(value: object) -> float | int | None:
    """Snap binary floating-point noise when a currency is effectively whole.

    Excel formula caches can expose values such as ``666000.0000000001``
    even when the source cell is formatted as a whole Rupiah amount.  Keep
    genuine fractional values intact, but canonicalize values within a tiny
    tolerance of the nearest Rupiah so they do not leak into Gold or BI.
    """

    number = normalize_money(value)
    if number is None:
        return None
    nearest = round(number)
    if math.isclose(number, nearest, rel_tol=0.0, abs_tol=1e-9):
        return int(nearest)
    return number
