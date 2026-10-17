"""Deterministic forecast behavior: balances, reserve breaches and category rules."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.forecast import ForecastWeek, forecast
from core.loaders import SyntheticCase, load_case
from core.schema import Assumptions, BusinessProfile, Customer, Payable, Receivable, Supplier, Transaction
from data.generate_synthetic import CASES

CASHFLOW_PAGE = Path(__file__).resolve().parents[1] / "app" / "pages" / "cashflow.py"


def _mini_case(transactions, *, receivables=None, payables=None, opening_cash=500.0, delays=0):
    customer = Customer(customer_id="C1", name="Synthetic Customer", typical_delay_days=delays)
    supplier = Supplier(supplier_id="S1", name="Synthetic Supplier")
    profile = BusinessProfile(
        business_id="SYN-TEST", business_name="Synthetic test", industry="Test",
        opening_cash=opening_cash, customers=[customer], suppliers=[supplier],
    )
    return SyntheticCase(
        transactions=transactions,
        receivables=receivables or [],
        payables=payables or [],
        profile=profile,
        expected={},
        assumptions=Assumptions(forecast_horizon_weeks=8, minimum_reserve_weeks=2),
    )


def _weekly_transactions(direction: str, category: str, amount: float, closing: float = 1_000.0):
    first = date(2026, 1, 5)
    return [
        Transaction(
            transaction_id=f"T-{week}", date=first + timedelta(weeks=week),
            description="Synthetic history", category=category, amount=amount,
            direction=direction, balance_after=closing - amount * (7 - week) if direction == "inflow" else closing + amount * (7 - week),
        )
        for week in range(8)
    ]


@pytest.mark.parametrize("case_name", CASES)
def test_demo_cases_match_qualitative_expectations(case_name):
    loaded = load_case(case_name)
    result = forecast(loaded)
    assert (result.shortage_week is not None) is loaded.expected["shortage_expected"]


def test_hand_calculated_weekly_projection_uses_last_actual_balance():
    case = _mini_case(_weekly_transactions("inflow", "Sales", 10, closing=1_000))
    result = forecast(case, horizon_weeks=8, reserve=100)
    assert result.opening_cash == 1_000
    assert result.forecast_weeks[0] == ForecastWeek(
        week_start=date(2026, 3, 2), layer="FORECAST", inflow=10, outflow=0, net=10, closing_balance=1_010,
    )


def test_invoice_and_bill_categories_are_not_projected_again_as_run_rate():
    history = _weekly_transactions("outflow", "Inventory", 100, closing=1_000)
    history += _weekly_transactions("inflow", "Sales", 200, closing=1_000)
    first_forecast_week = date(2026, 3, 2)
    case = _mini_case(
        history,
        receivables=[Receivable(invoice_id="I1", customer_id="C1", issue_date=date(2026, 2, 1),
                                due_date=first_forecast_week, amount=300)],
        payables=[Payable(bill_id="B1", supplier_id="S1", issue_date=date(2026, 2, 1),
                          due_date=first_forecast_week, amount=100, category="Inventory")],
    )
    result = forecast(case)
    assert result.forecast_weeks[0].inflow == 300
    assert result.forecast_weeks[0].outflow == 100


def test_reserve_change_moves_first_shortage_week():
    case = _mini_case(_weekly_transactions("outflow", "Rent", 100, closing=1_000))
    low_reserve = forecast(case, horizon_weeks=13, reserve=100)
    higher_reserve = forecast(case, horizon_weeks=13, reserve=300)
    assert low_reserve.shortage_week == 10
    assert higher_reserve.shortage_week == 8


def test_payment_delay_uses_median_after_three_paid_invoices():
    transactions = _weekly_transactions("inflow", "Sales", 10)
    invoices = [
        Receivable(invoice_id=f"I{i}", customer_id="C1", issue_date=date(2025, 12, 1),
                   due_date=date(2025, 12, 20), amount=10,
                   paid_date=date(2025, 12, 20) + timedelta(days=delay), paid_amount=10)
        for i, delay in enumerate((2, 8, 14), start=1)
    ]
    result = forecast(_mini_case(transactions, receivables=invoices, delays=60), reserve=0)
    assert result.payment_delay_days["C1"] == 8


def test_forecast_is_deterministic_and_horizon_is_at_least_eight_weeks():
    case = _mini_case(_weekly_transactions("inflow", "Sales", 10))
    assert forecast(case) == forecast(case)
    with pytest.raises(ValueError, match="at least 8"):
        forecast(case, horizon_weeks=7)


def test_cashflow_page_renders_for_all_five_demo_cases():
    app = AppTest.from_file(CASHFLOW_PAGE, default_timeout=20).run()
    assert not app.exception
    for case_name in CASES:
        app.selectbox[0].select(case_name).run(timeout=20)
        assert not app.exception
        assert app.session_state["active_synthetic_case"] == case_name
        assert app.session_state["cash_flow_forecast"].forecast_weeks
        uncertainty = app.session_state["cash_flow_uncertainty"]
        assert len(uncertainty.p10) == len(app.session_state["cash_flow_forecast"].forecast_weeks)
        assert all(low <= high for low, high in zip(uncertainty.p10, uncertainty.p90))


def test_cashflow_reserve_input_recalculates_shortage_week():
    app = AppTest.from_file(CASHFLOW_PAGE, default_timeout=20).run()
    assert app.session_state["cash_flow_forecast"].shortage_week is None
    app.number_input[0].set_value(6_000_000).run(timeout=20)
    assert app.session_state["cash_flow_forecast"].shortage_week == 1


def test_cashflow_sales_variability_widens_uncertainty_band():
    app = AppTest.from_file(CASHFLOW_PAGE, default_timeout=30).run()
    before = app.session_state["cash_flow_uncertainty"]
    before_width = max(hi - lo for lo, hi in zip(before.p10, before.p90))
    app.slider[0].set_value(0.8).run(timeout=30)
    after = app.session_state["cash_flow_uncertainty"]
    after_width = max(hi - lo for lo, hi in zip(after.p10, after.p90))
    assert after_width > before_width
