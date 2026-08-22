import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "superset-dashboard" / "lib" / "_shared.py"
MODULE_SPEC = importlib.util.spec_from_file_location("superset_dashboard_shared", MODULE_PATH)
SHARED = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC.loader is not None
MODULE_SPEC.loader.exec_module(SHARED)


def _metric(column_name: str, aggregate: str = "SUM") -> dict:
    return {"column": {"column_name": column_name}, "aggregate": aggregate}


def test_count_metrics_are_not_currency_formatted():
    assert SHARED._guess_format(_metric("jumlah_item")) == "integer"
    assert SHARED._guess_format(_metric("jumlah_iku")) == "integer"
    assert SHARED._guess_format(_metric("jumlah_kegiatan")) == "integer"


def test_budget_metrics_keep_currency_formatting():
    assert SHARED._guess_format(_metric("total_anggaran")) == "currency"
