"""Every Streamlit page must run without raising (T02).

Layout bugs only surface when the whole page executes, so each stub is driven
by AppTest instead of being inspected for markup.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGES_DIR = Path(__file__).with_name("tests").resolve().parents[1] / "app" / "pages"


def _pages() -> list[Path]:
    return sorted(PAGES_DIR.glob("*.py"))


TESTS = [str(page) for page in _pages()]
IDS = [Path(page).stem for page in _pages()]


def test_pages_dir_is_populated() -> None:
    """A missing pages/ directory would make the loop below pass vacuously."""
    assert len(TESTS) == 10, f"expected 10 pages, found {len(TESTS)}: {TESTS}"


@pytest.mark.parametrize("page", TESTS, ids=IDS)
def test_page_runs_without_exception(page: str) -> None:
    at = AppTest.from_file(page, default_timeout=30).run()
    assert not at.exception, f"{page} raised:\n" + "\n".join(
        f"{e.value}\n{e.stack_trace}" for e in at.exception
    )
