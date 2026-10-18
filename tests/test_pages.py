"""Every Streamlit page must run without raising (T02).

Layout bugs only surface when the whole page executes, so each stub is driven
by AppTest instead of being inspected for markup.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.loaders import load_case
from data.generate_synthetic import CASES
from services.auth import AUTH_SESSION_KEY, DEMO_PASSWORD_DEFAULTS, login

PAGES_DIR = Path(__file__).with_name("tests").resolve().parents[1] / "app" / "pages"
ROLES = ("owner", "finance_ops", "viewer", "auditor")
DATA_PAGES = {"cashflow", "lab", "financing", "analysis", "copilot", "assumptions"}
CASE_WIDGETS = {
    "overview": "overview-case-select", "cashflow": "cashflow-case-select", "lab": "lab-case-select",
    "financing": "financing-case-select", "analysis": "analysis-case-select",
    "copilot": "copilot-case-select", "assumptions": "assumptions-case-select",
    "upload": "upload-demo-case-select",
}


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


@pytest.mark.parametrize("page", TESTS, ids=IDS)
@pytest.mark.parametrize("role", ROLES)
def test_all_pages_all_cases_all_roles(page: str, role: str, monkeypatch, tmp_path) -> None:
    """Each page must survive the full case and role matrix without bypassing permissions."""
    monkeypatch.setenv("STRATIFY_AUDIT_DB", str(tmp_path / f"audit-{role}.sqlite3"))
    monkeypatch.setenv("STRATIFY_AGENT_ACTIONS_DB", str(tmp_path / f"actions-{role}.sqlite3"))
    monkeypatch.setenv("STRATIFY_SANDBOX_LOG", str(tmp_path / f"sandbox-{role}.jsonl"))
    state = {}
    login(role, DEMO_PASSWORD_DEFAULTS[role], session_state=state,
          db_path=tmp_path / f"audit-{role}.sqlite3")
    at = AppTest.from_file(page, default_timeout=45)
    at.session_state[AUTH_SESSION_KEY] = state[AUTH_SESSION_KEY]
    stem = Path(page).stem
    for case_name in CASES:
        at.session_state["active_synthetic_case"] = case_name
        at.session_state["synthetic_case_data"] = load_case(case_name)
        at.session_state["global-business-selector"] = case_name
        if stem in CASE_WIDGETS:
            at.session_state[CASE_WIDGETS[stem]] = case_name
        at.run(timeout=45)
        assert not at.exception, f"{page} failed for role={role}, case={case_name}: " + "\n".join(
            f"{e.value}\n{e.stack_trace}" for e in at.exception
        )
        if stem in DATA_PAGES:
            assert at.session_state["active_synthetic_case"] == case_name


@pytest.mark.parametrize("page", [str(PAGES_DIR / f"{name}.py") for name in sorted(DATA_PAGES)])
def test_case_pages_show_empty_state_without_loaded_data(page: str, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STRATIFY_AUDIT_DB", str(tmp_path / "audit.sqlite3"))
    state = {}
    login("owner", DEMO_PASSWORD_DEFAULTS["owner"], session_state=state,
          db_path=tmp_path / "audit.sqlite3")
    at = AppTest.from_file(page, default_timeout=45)
    at.session_state[AUTH_SESSION_KEY] = state[AUTH_SESSION_KEY]
    at.session_state["active_synthetic_case"] = None
    at.session_state["global-business-selector"] = None
    at.run(timeout=45)
    assert not at.exception
    assert any("No data loaded" in item.value for item in at.markdown), page
