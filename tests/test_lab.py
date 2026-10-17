"""Known-number and selection tests for the deterministic Decision Lab engine."""
import json
from datetime import date, timedelta

import pytest

from core.financing import FinancingTerms
from core.lab import LabAssumptions, run_lab
from core.loaders import SyntheticCase
from core.schema import Assumptions, BusinessProfile, Customer, Payable, Receivable, Supplier, Transaction


def _case(*, healthy: bool = False) -> SyntheticCase:
    first = date(2026, 1, 5)
    transactions = [
        Transaction(transaction_id=f"T{i}", date=first + timedelta(weeks=i), description="History",
                    category="Rent", amount=10 if healthy else 200, direction="outflow", balance_after=1_000)
        for i in range(8)
    ]
    profile = BusinessProfile(
        business_id="MINI", business_name="Mini business", industry="Test", opening_cash=1_000,
        customers=[Customer(customer_id="C1", name="Customer", typical_delay_days=70)],
        suppliers=[Supplier(supplier_id="S1", name="Supplier")],
    )
    receivables = [] if healthy else [Receivable(
        invoice_id="I1", customer_id="C1", issue_date=date(2026, 1, 1), due_date=date(2026, 2, 2), amount=400,
    )]
    payables = [] if healthy else [Payable(
        bill_id="B1", supplier_id="S1", issue_date=date(2026, 2, 1), due_date=date(2026, 3, 2),
        amount=300, category="Optional", deferrable=True, discretionary=True,
    )]
    assumptions = Assumptions(forecast_horizon_weeks=8, minimum_reserve_weeks=2)
    return SyntheticCase(transactions, receivables, payables, profile, {}, assumptions)


def test_known_scenario_has_expected_original_gap_and_shortage():
    result = run_lab(_case())
    baseline = result.plans["Option 0"]
    assert baseline.funding_gap == pytest.approx(900)
    assert baseline.shortage_week == 2
    assert baseline.remaining_gap == pytest.approx(900)
    assert baseline.balance_series_before[-1].closing_balance == pytest.approx(-500)


def test_isolated_levers_are_computed_separately_and_combined_impact_is_bounded():
    result = run_lab(_case())
    assert {"L1", "L2", "L3", "Option A"} <= set(result.plans)
    isolated_minima = [min(point.closing_balance for point in result.plans[key].balance_series_after)
                       for key in ("L1", "L2", "L3")]
    combined_minimum = min(point.closing_balance for point in result.plans["Option A"].balance_series_after)
    assert combined_minimum >= max(isolated_minima)
    # L1 moves 50% of the 400 BDT overdue invoice forward without counting it twice.
    assert result.plans["L1"].balance_series_after[-1].closing_balance == pytest.approx(-500)


def test_option_b_finances_only_the_remaining_gap_and_is_no_larger_than_c():
    result = run_lab(_case())
    assert result.plans["Option B"].funding_gap < result.plans["Option C"].funding_gap
    assert result.plans["Option B"].financing_amount <= result.plans["Option C"].financing_amount


def test_best_plan_selection_uses_feasibility_then_cost_and_reason():
    result = run_lab(_case(healthy=True))
    assert result.plans["Option 0"].is_feasible
    assert result.best_plan_id == "Option 0"
    assert "lowest modelled cost" in result.best_plan_reason
    assert result.borrowing_necessary is False


def test_no_feasible_plan_reports_smallest_remaining_gap():
    result = run_lab(_case(), LabAssumptions(financing_terms=FinancingTerms(100, 100, 1)))
    assert not any(result.plans[key].is_feasible for key in ("Option 0", "Option A", "Option B", "Option C"))
    assert "No plan fully closes the gap" in result.best_plan_reason
    assert result.plans[result.best_plan_id].remaining_gap == min(
        result.plans[key].remaining_gap for key in ("Option 0", "Option A", "Option B", "Option C")
    )


def test_result_is_deterministic_serializable_and_hypothetical():
    left = run_lab(_case())
    right = run_lab(_case())
    assert left == right
    rendered = left.to_dict()
    json.dumps(rendered)
    assert rendered["best_plan_id"] == left.best_plan_id
    assert len(rendered["key_answers"]) == 5
    assert all(plan.layer_tags == ("HYPOTHETICAL",) for plan in left.plans.values())
    assert all(plan.breach_probability is None for plan in left.plans.values())


@pytest.mark.parametrize("settings", [
    LabAssumptions(collection_pct=101), LabAssumptions(collection_weeks=0),
    LabAssumptions(deferral_weeks=1.5), LabAssumptions(discretionary_reduction_pct=-1),
    LabAssumptions(financing_template="Unknown"),
])
def test_invalid_lab_assumptions_are_rejected(settings):
    with pytest.raises(ValueError):
        run_lab(_case(), settings)
