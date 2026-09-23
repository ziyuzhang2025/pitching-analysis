"""Every test in this folder is an exercise for Ziyu (see docs/backend_exercises.md)."""

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/exercises/" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.ziyu)
