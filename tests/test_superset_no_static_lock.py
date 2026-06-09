import json

from src.sql import setup_superset_dashboard as dashboard


def test_superset_charts_have_no_static_prodi_or_year_lock():
    definitions = dashboard._chart_definitions(dataset_id=42)

    assert dashboard._chart_static_locks(definitions) == []

    for item in definitions:
        params = json.loads(item["params"])
        context = json.loads(item["query_context"])
        assert params.get("adhoc_filters") == []
        for query in context["queries"]:
            assert query.get("filters") == []
