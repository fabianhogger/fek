import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def fixture(fek_id: str) -> str:
    """Path to a fixture PDF, skipping the test if it has not been fetched."""
    path = os.path.join(FIXTURES, f"{fek_id}.pdf")
    if not os.path.exists(path):
        pytest.skip(f"{fek_id}.pdf missing — run: python scripts/fetch_fixtures.py")
    return path
