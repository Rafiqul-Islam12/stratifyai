"""Hand-calculated financing schedules and page behavior."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.financing import FinancingTerms, annuity_payment, calculate_financing, funding_amount
from core.forecast import ForecastResult, ForecastWeek
from core.loaders import load_case

PAGE = Path(__file__).resolve().parents[1] / "app" / "pages" / "financing.py"


def _forecast(net: float = 20_000) -> ForecastResult:
    week = ForecastWeek(__import__("datetime").date(2026, 1, 5), "FORECAST", net, 0, net, 1_000)
    return ForecastResult([week], [], [week], 1_000, 0, 0, 0, 8, None, None, None,
                          1_000, 0, 0, 0, "none", {}, {})


def test_standard_annuity_payment_and_total_interest_hand_calculated():
    payment = annuity_payment(100_000, 12, 12)
    assert payment == pytest.approx(8_884.8789, abs=0.01)
    result = calculate_financing("Term loan", 100_000, FinancingTerms(12, 0, 12), _forecast())
    assert len(result.schedule) == 12
    assert result.schedule[0].interest == pytest.approx(1_000)
    assert sum(row.payment for row in result.schedule) == pytest.approx(payment * 12, abs=0.01)
    assert result.interest == pytest.approx(payment * 12 - 100_000, abs=0.02)
    assert result.schedule[-1].closing_balance == 0


def test_zero_rate_has_equal_principal_installments():
    result = calculate_financing("Term loan", 12_000, FinancingTerms(0, 0, 3), _forecast())
    assert [row.payment for row in result.schedule] == pytest.approx([4_000] * 3)
    assert result.interest == result.fees == result.total_cost == 0


def test_zero_gap_creates_no_facility_or_debt_service():
    result = calculate_financing("Term loan", 0, FinancingTerms(), _forecast())
    assert result.amount == result.total_repayment == 0
    assert result.schedule == ()
    assert result.capacity_ratio is None
    assert result.pressure_label == "No repayment"


def test_gap_rounds_up_and_invoice_finance_grosses_up_for_advance():
    assert funding_amount(100_001, "Term loan") == 101_000
    assert funding_amount(100_001, "Invoice financing", 80) == pytest.approx(126_250)


@pytest.mark.parametrize("terms", [
    FinancingTerms(-1, 1, 6), FinancingTerms(12, -1, 6), FinancingTerms(12, 1, 0),
    FinancingTerms(12, 1, 6, 0), FinancingTerms(101, 1, 6),
])
def test_invalid_terms_are_rejected(terms):
    with pytest.raises(ValueError):
        calculate_financing("Term loan", 10_000, terms, _forecast())


def test_financing_page_renders_case_three_and_reacts_to_rate_and_tenor():
    app = AppTest.from_file(PAGE, default_timeout=30).run()
    assert not app.exception
    assert app.session_state["active_synthetic_case"] == "high_expense_shortage"
    initial = app.session_state["financing_result"]
    assert initial.amount > 0
    assert len(initial.schedule) == 6
    app.number_input[1].set_value(20.0).run(timeout=30)
    after_rate = app.session_state["financing_result"]
    assert after_rate.total_cost > initial.total_cost
    app.number_input[0].set_value(12).run(timeout=30)
    after_tenor = app.session_state["financing_result"]
    assert len(after_tenor.schedule) == 12
    assert after_tenor.total_cost != after_rate.total_cost


def test_all_templates_calculate_with_case_three():
    case = load_case("high_expense_shortage")
    from core.forecast import forecast

    projection = forecast(case)
    for template in ("Term loan", "Invoice financing", "Supplier credit", "Credit line"):
        result = calculate_financing(template, projection.funding_gap, FinancingTerms(), projection)
        assert result.amount >= projection.funding_gap
        assert result.total_cost >= 0
