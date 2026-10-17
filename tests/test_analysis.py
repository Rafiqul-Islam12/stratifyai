"""Hand-computed business indicators, watchlist scores and readiness packs."""
from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.analysis import analyze
from core.forecast import forecast
from core.loaders import SyntheticCase, load_case
from core.readiness import assess_readiness
from core.readiness_pack import build_readiness_pack, verify_readiness_pack
from core.schema import Assumptions, BusinessProfile, Customer, Payable, Receivable, Supplier, Transaction
from core.watchlist import receivables_watchlist

ANALYSIS_PAGE = Path(__file__).resolve().parents[1] / "app" / "pages" / "analysis.py"
FINANCING_PAGE = Path(__file__).resolve().parents[1] / "app" / "pages" / "financing.py"
AS_OF = date(2026, 3, 2)


def _case(*, receivables=True):
    first = date(2026, 1, 5)
    transactions = []
    balance = 500.0
    for week in range(8):
        day = first + timedelta(weeks=week)
        balance += 100
        transactions.append(Transaction(transaction_id=f"I{week}", date=day, description="Sales", category="Sales",
            amount=100, direction="inflow", balance_after=balance))
        balance -= 80
        transactions.append(Transaction(transaction_id=f"O{week}", date=day + timedelta(days=1), description="Stock",
            category="Inventory", amount=80, direction="outflow", balance_after=balance))
    invoices = []
    if receivables:
        for key, days, amount, paid in (("I1", 10, 100, 40), ("I2", 40, 50, 0),
                                        ("I3", 90, 30, 0), ("I4", 100, 20, 0),
                                        ("I5", -7, 500, 0)):
            due = AS_OF - timedelta(days=days)
            invoices.append(Receivable(invoice_id=key, customer_id="C1", issue_date=due-timedelta(days=30),
                due_date=due, amount=amount, paid_amount=paid,
                paid_date=due+timedelta(days=5) if paid else None))
    payables = [
        Payable(bill_id="B1", supplier_id="S1", issue_date=AS_OF-timedelta(days=40),
            due_date=AS_OF-timedelta(days=29), amount=20, paid_amount=0, category="Inventory"),
        Payable(bill_id="B2", supplier_id="S1", issue_date=AS_OF-timedelta(days=10),
            due_date=AS_OF+timedelta(days=14), amount=30, paid_amount=0, category="Inventory"),
    ]
    profile = BusinessProfile(business_id="TEST", business_name="Test business", industry="Retail",
        opening_cash=500, customers=[Customer(customer_id="C1", name="Customer 1", typical_delay_days=10),
        Customer(customer_id="C2", name="Customer 2", typical_delay_days=0)],
        suppliers=[Supplier(supplier_id="S1", name="Supplier 1")])
    return SyntheticCase(transactions, invoices, payables, profile, {},
                         Assumptions(forecast_horizon_weeks=8, minimum_reserve_weeks=2))


def test_analysis_metrics_match_hand_calculation_and_aging_boundaries():
    result = analyze(_case(), as_of=AS_OF)
    assert result.income == pytest.approx(800)
    assert result.expenses == pytest.approx(640)
    assert result.net_cash_flow == pytest.approx(160)
    assert result.receivables_open == pytest.approx(660)
    assert result.receivables_overdue == pytest.approx(160)
    assert result.aging == {"0-30 days": 60, "31-60 days": 50, "61-90 days": 30, "90+ days": 20}
    assert result.payables_open == pytest.approx(50)
    assert result.payables_due_next_4_weeks == pytest.approx(50)
    assert result.gross_margin_pct.value == pytest.approx(20)
    assert result.dso_days.value == pytest.approx(660 / 600 * 57)
    assert result.dpo_days.value == pytest.approx(57)


def test_metrics_return_reasons_when_the_data_cannot_support_them():
    case = load_case("stable_healthy")
    case = SyntheticCase([], [], [], case.profile, {}, case.assumptions)
    result = analyze(case, as_of=AS_OF)
    assert result.burn_rate_weekly.value is None
    assert result.runway_weeks.value is None
    assert result.gross_margin_pct.value is None
    assert result.customer_concentration_pct.value is None
    assert all(metric.reason for metric in (result.burn_rate_weekly, result.runway_weeks,
        result.gross_margin_pct, result.customer_concentration_pct, result.dso_days, result.dpo_days))


def test_delayed_case_watchlist_is_ordered_and_shows_invoice_evidence():
    case = load_case("delayed_customer_payments")
    watchlist = receivables_watchlist(case)
    assert watchlist
    assert [row.score for row in watchlist] == sorted((row.score for row in watchlist), reverse=True)
    assert all(row.invoice_ids and 0 <= row.score <= 100 for row in watchlist)
    assert all(row.label in {"Normal", "Watch", "Urgent"} for row in watchlist)


def test_readiness_and_pack_hash_verifies_then_detects_content_edit():
    case = load_case("high_expense_shortage")
    projection = forecast(case)
    analysis = analyze(case)
    readiness = assess_readiness(case, analysis, projection, capacity_ratio=1.0)
    assert 0 <= readiness.score <= 100
    assert "not a loan approval prediction" in readiness.label
    pack = build_readiness_pack(case, analysis, projection, readiness, chosen_plan="Option A",
        assumptions={"reserve": projection.reserve}, expires_on=date.today()+timedelta(days=10), consent=True)
    assert verify_readiness_pack(pack.content)[0]
    edited = pack.content.replace("StratifyAI Readiness Pack", "StratifyAI Readiness PacK", 1)
    assert not verify_readiness_pack(edited)[0]
    assert not verify_readiness_pack(pack.content + "edited")[0]


def test_analysis_page_renders_all_five_cases():
    app = AppTest.from_file(ANALYSIS_PAGE, default_timeout=30).run()
    assert not app.exception
    for name in ("stable_healthy", "delayed_customer_payments", "high_expense_shortage", "import_financing", "sales_drop_cost_rise"):
        app.selectbox[0].select(name).run(timeout=30)
        assert not app.exception
        assert app.session_state["active_synthetic_case"] == name


def test_financing_page_exposes_readiness_and_pack_tools():
    app = AppTest.from_file(FINANCING_PAGE, default_timeout=40).run()
    assert not app.exception
    assert app.button[0].label == "Generate readiness pack"
    app.checkbox[0].check().run(timeout=40)
    app.button[0].click().run(timeout=40)
    assert "Content SHA-256:" in app.session_state["readiness_pack_content"]
    assert verify_readiness_pack(app.session_state["readiness_pack_content"])[0]


def test_financing_page_renders_readiness_for_all_demo_cases():
    app = AppTest.from_file(FINANCING_PAGE, default_timeout=45).run()
    assert not app.exception
    for name in ("stable_healthy", "delayed_customer_payments", "high_expense_shortage", "import_financing", "sales_drop_cost_rise"):
        app.selectbox[0].select(name).run(timeout=45)
        assert not app.exception
        assert any(metric.label == "Readiness indicator" for metric in app.metric)
