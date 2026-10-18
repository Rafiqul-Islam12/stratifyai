"""T14 Overview integration and empty-state coverage."""
from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from services.auth import AUTH_SESSION_KEY, DEMO_PASSWORD_DEFAULTS, login

OVERVIEW = Path(__file__).resolve().parents[1] / "app" / "pages" / "overview.py"


def _signed_in_app(role: str, audit_path: Path) -> AppTest:
    state = {}
    login(role, DEMO_PASSWORD_DEFAULTS[role], session_state=state, db_path=audit_path)
    app = AppTest.from_file(OVERVIEW, default_timeout=45)
    app.session_state[AUTH_SESSION_KEY] = state[AUTH_SESSION_KEY]
    return app


def test_overview_empty_state_and_all_five_cases(monkeypatch, tmp_path):
    audit_path = tmp_path / "overview-audit.sqlite3"
    monkeypatch.setenv("STRATIFY_AUDIT_DB", str(audit_path))
    app = _signed_in_app("owner", audit_path).run()
    assert not app.exception
    assert any("No data loaded" in item.value for item in app.markdown)

    for case_name in ("stable_healthy", "delayed_customer_payments", "high_expense_shortage",
                      "import_financing", "sales_drop_cost_rise"):
        app.selectbox(key="overview-case-select").select(case_name).run()
        app.button(key="overview-load-demo").click().run(timeout=45)
        assert not app.exception, case_name
        assert app.session_state["active_synthetic_case"] == case_name
        assert all(label in "\n".join(item.value for item in app.markdown)
                   for label in ("Current cash", "Funding gap", "Receivables aging", "Pending approvals"))
        assert app.session_state["synthetic_case_data"].profile.business_name
