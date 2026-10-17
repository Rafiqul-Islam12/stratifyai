"""Deterministic stress shocks and editable case 4 import events."""
from dataclasses import replace

import pytest

from core.forecast import forecast
from core.import_scenario import build_import_scenario, default_import_inputs
from core.loaders import load_case
from core.stress import StressInputs, apply_stress


def test_stress_decreases_sales_increases_costs_and_delays_open_invoices():
    case = load_case("high_expense_shortage")
    base = forecast(case)
    stressed = apply_stress(case, StressInputs(20, 15, 30, 0))
    projected = forecast(stressed.case)
    assert projected.opening_cash == base.opening_cash
    assert projected.funding_gap >= base.funding_gap
    open_before = next(row for row in case.receivables if row.paid_amount < row.amount)
    open_after = next(row for row in stressed.case.receivables if row.invoice_id == open_before.invoice_id)
    assert open_after.due_date > open_before.due_date
    assert open_after.amount - open_after.paid_amount == pytest.approx(
        (open_before.amount - open_before.paid_amount) * 0.8,
    )


def test_fx_shock_only_changes_import_linked_costs_in_import_case():
    case = load_case("import_financing")
    result = apply_stress(case, StressInputs(fx_shock_pct=10))
    before = next(row for row in case.payables if row.category == "Inventory" and row.paid_amount < row.amount)
    after = next(row for row in result.case.payables if row.bill_id == before.bill_id)
    assert after.amount - after.paid_amount == pytest.approx((before.amount - before.paid_amount) * 1.1)
    stable = apply_stress(load_case("stable_healthy"), StressInputs(fx_shock_pct=10))
    assert stable.case.payables == load_case("stable_healthy").payables
    assert any("does not change" in note for note in stable.risk_notes)


def test_stress_rejects_out_of_range_values():
    with pytest.raises(ValueError):
        apply_stress(load_case("stable_healthy"), StressInputs(sales_drop_pct=101))
    with pytest.raises(ValueError):
        apply_stress(load_case("stable_healthy"), StressInputs(customer_delay_days=-1))


def test_case_four_import_defaults_generate_hypothetical_deposit_landed_cost_and_sales():
    case = load_case("import_financing")
    inputs = default_import_inputs(case)
    result = build_import_scenario(case, inputs)
    assert result.product_cost_bdt == pytest.approx(1_250_000)
    assert result.shipping_cost_bdt == pytest.approx(180_000)
    assert result.deposit_bdt == pytest.approx(375_000)
    assert result.landed_cost_bdt == pytest.approx(1_430_000)
    assert result.events[0].layer == "HYPOTHETICAL"
    assert {event.event for event in result.events} >= {"Import deposit", "Remaining product, shipping and duties/taxes", "Hypothetical sales collection"}
    assert len(result.scenario_case.payables) == len(case.payables) + 2
    assert len(result.scenario_case.receivables) > len(case.receivables)


def test_import_fx_shock_deposit_and_duty_inputs_recalculate_cash_events():
    case = load_case("import_financing")
    defaults = default_import_inputs(case)
    changed = replace(defaults, deposit_pct=50, duties_taxes_pct=10, fx_shock_pct=10)
    result = build_import_scenario(case, changed)
    assert result.product_cost_bdt == pytest.approx(1_375_000)
    assert result.deposit_bdt == pytest.approx(687_500)
    assert result.duties_taxes_bdt == pytest.approx(157_300)
    assert result.landed_cost_bdt == pytest.approx(1_730_300)
    assert result.shocked_fx_rate == pytest.approx(134.2)


@pytest.mark.parametrize("changes", [
    {"deposit_pct": 101}, {"duties_taxes_pct": -1}, {"fx_rate_bdt_per_unit": 0},
    {"lead_time_weeks": 0}, {"sales_ramp_weeks": 53}, {"collection_delay_days": 366},
])
def test_import_scenario_rejects_invalid_inputs(changes):
    case = load_case("import_financing")
    with pytest.raises(ValueError):
        build_import_scenario(case, replace(default_import_inputs(case), **changes))
