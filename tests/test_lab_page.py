"""Streamlit smoke and interaction tests for the Lab and assumption store."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from services.auth import AUTH_SESSION_KEY, DEMO_PASSWORD_DEFAULTS, login

LAB_PAGE = Path(__file__).resolve().parents[1] / "app" / "pages" / "lab.py"
ASSUMPTIONS_PAGE = Path(__file__).resolve().parents[1] / "app" / "pages" / "assumptions.py"


def test_lab_page_renders_all_five_cases():
    app = AppTest.from_file(LAB_PAGE, default_timeout=30).run()
    assert not app.exception
    assert app.session_state["lab_case_name"] == "high_expense_shortage"
    for case_name in ("stable_healthy", "delayed_customer_payments", "import_financing", "sales_drop_cost_rise"):
        app.selectbox[0].select(case_name).run(timeout=30)
        assert not app.exception
        assert app.session_state["lab_case_name"] == case_name
        assert set(app.session_state["lab_result"].plans) >= {"Option 0", "Option A", "Option B", "Option C"}
        assert all(plan.breach_probability is not None for plan in app.session_state["lab_result"].plans.values())


def test_lab_decision_report_is_downloadable_and_uses_current_results(monkeypatch, tmp_path):
    audit_db = tmp_path / "audit.sqlite3"
    monkeypatch.setenv("STRATIFY_AUDIT_DB", str(audit_db))
    state = {}
    login("owner", DEMO_PASSWORD_DEFAULTS["owner"], session_state=state, db_path=audit_db)
    app = AppTest.from_file(LAB_PAGE, default_timeout=30)
    app.session_state[AUTH_SESSION_KEY] = state[AUTH_SESSION_KEY]
    app.run()
    assert not app.exception
    buttons = app.get("download_button")
    assert len(buttons) == 1
    assert buttons[0].label == "Download decision report (Markdown)"
    report = app.session_state["lab_decision_report"]
    assert "Synthetic data" in report
    assert "ACTUAL records, FORECAST outputs, HYPOTHETICAL plan changes" in report
    assert app.session_state["lab_result"].best_plan_id in report
    assert "scenario.changed event" in report
    assert "not a lender decision" in report
    buttons[0].click().run()
    assert app.get("download_button")[0].value is True


def test_lab_sales_stress_recalculates_plan_results():
    app = AppTest.from_file(LAB_PAGE, default_timeout=30).run()
    before = app.session_state["lab_result"].plans["Option 0"].funding_gap
    app.slider(key="lab::high_expense_shortage::stress_sales_drop_pct").set_value(20).run(timeout=30)
    after = app.session_state["lab_result"].plans["Option 0"].funding_gap
    assert after > before
    gap_before_lever_edit = app.session_state["lab_result"].plans["Option A"].remaining_gap
    app.slider(key="lab::high_expense_shortage::discretionary_reduction_pct").set_value(40).run(timeout=30)
    assert app.session_state["lab_result"].plans["Option A"].remaining_gap < gap_before_lever_edit


def test_lab_reserve_basis_slider_updates_reserve_and_cards():
    app = AppTest.from_file(LAB_PAGE, default_timeout=30).run()
    original = app.session_state["lab_result"].reserve
    app.slider(key="lab::high_expense_shortage::reserve_weeks").set_value(4.0).run(timeout=30)
    assert app.session_state["lab_result"].reserve > original


def test_lab_sales_variability_edit_recomputes_plan_probabilities():
    app = AppTest.from_file(LAB_PAGE, default_timeout=30).run()
    before = app.session_state["lab_result"].plans["Option 0"].breach_probability
    app.slider(key="lab::high_expense_shortage::sales_variability_cv").set_value(0.5).run(timeout=30)
    after = app.session_state["lab_result"].plans["Option 0"].breach_probability
    assert after is not None and before is not None
    assert app.session_state["lab_result"].plans["Option 0"].breach_probability_by_week


def test_lab_case_four_fx_and_deposit_edits_change_import_events():
    app = AppTest.from_file(LAB_PAGE, default_timeout=30).run()
    app.selectbox[0].select("import_financing").run(timeout=30)
    original = app.session_state["lab_import_result"]
    app.slider(key="lab::import_financing::import_fx_shock_pct").set_value(10).run(timeout=30)
    after_fx = app.session_state["lab_import_result"]
    assert after_fx.product_cost_bdt > original.product_cost_bdt
    app.slider(key="lab::import_financing::import_deposit_pct").set_value(50).run(timeout=30)
    after_deposit = app.session_state["lab_import_result"]
    assert after_deposit.deposit_bdt > after_fx.deposit_bdt


def test_lab_can_save_three_scenarios_and_proposal_stays_disabled():
    app = AppTest.from_file(LAB_PAGE, default_timeout=30).run()
    assert app.button[1].disabled
    for index in range(3):
        app.text_input(key="lab-save-name-high_expense_shortage").set_value(f"Saved {index + 1}")
        app.button[0].click().run(timeout=30)
        assert len(app.session_state["lab_saved_scenarios"]["high_expense_shortage"]) == index + 1
    assert app.button[0].disabled


def test_assumptions_page_edits_and_reset_restore_defaults():
    app = AppTest.from_file(ASSUMPTIONS_PAGE, default_timeout=30).run()
    assert not app.exception
    original = app.session_state["stratify_assumptions_by_case"]["high_expense_shortage"]["collection_pct"]
    app.slider(key="assumptions::high_expense_shortage::collection_pct").set_value(75).run(timeout=30)
    assert app.session_state["stratify_assumptions_by_case"]["high_expense_shortage"]["collection_pct"] == 75
    app.button[0].click().run(timeout=30)
    assert app.session_state["stratify_assumptions_by_case"]["high_expense_shortage"]["collection_pct"] == original
