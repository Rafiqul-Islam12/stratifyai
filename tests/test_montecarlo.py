"""Deterministic and probability-boundary checks for the uncertainty model."""
from dataclasses import replace

import pytest

from core.forecast import forecast
from core.loaders import load_case
from core.montecarlo import simulate


def test_seed_repeats_same_simulation_and_percentiles_are_ordered():
    case = load_case("high_expense_shortage")
    result = simulate(case)
    assert result == simulate(case)
    assert all(a <= b <= c for a, b, c in zip(result.p10, result.p50, result.p90))


def test_zero_variability_collapses_to_deterministic_path_without_invoices():
    case = replace(load_case("stable_healthy"), receivables=[])
    projection = forecast(case)
    result = simulate(case, projection=projection, sales_variability_cv=0, customer_delay_sd_days=0)
    assert result.p10 == pytest.approx(tuple(row.closing_balance for row in projection.forecast_weeks))
    assert result.p50 == pytest.approx(result.p10)
    assert result.p90 == pytest.approx(result.p10)


def test_probabilities_are_bounded_and_more_cash_does_not_increase_breach_chance():
    case = load_case("high_expense_shortage")
    projection = forecast(case)
    base = simulate(case, projection=projection)
    more_cash = simulate(case, projection=projection, balance_adjustments=[100_000] * projection.horizon_weeks)
    assert all(0 <= probability <= 1 for probability in (*base.probability_below_reserve, *base.probability_below_zero))
    assert more_cash.probability_any_reserve_breach <= base.probability_any_reserve_breach
