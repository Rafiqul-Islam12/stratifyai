"""Streamlit smoke and interaction tests for the Lab and assumption store."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

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


def test_lab_sales_stress_recalculates_plan_results():
    app = AppTest.from_file(LAB_PAGE, default_timeout=30).run()
    before = app.session_state["lab_result"].plans["Option 0"].funding_gap
    app.slider(key="lab::high_expense_shortage::stress_sales_drop_pct").set_value(20).run(timeout=30)
    after = app.session_state["lab_result"].plans["Option 0"].funding_gap
    assert after > before


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
