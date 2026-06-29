# Context7 Notes - Current Stack

## Flask

Context7 library: `/pallets/flask`.

- Flask routes can return serializable `dict`/`list` responses as JSON.
- `jsonify` remains appropriate for explicit JSON responses.
- Optional JSON request bodies should be read defensively with `request.get_json(silent=True)` when the route accepts empty bodies.

## Pytest

Context7 library: `/pytest-dev/pytest`.

- Test discovery follows `test_*.py` conventions.
- After deleting obsolete tests, run explicit suite paths with `python -m pytest tests`.
- Use focused paths first for rapid feedback, then run the full suite before commit.
