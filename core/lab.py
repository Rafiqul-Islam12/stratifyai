"""Deterministic, explainable what-if comparison engine for the Decision Lab."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from datetime import date, timedelta
from typing import Any

from core.financing import TEMPLATES, FinancingTerms, calculate_financing
from core.forecast import ForecastResult, forecast
from core.loaders import SyntheticCase


@dataclass(frozen=True)
class LabAssumptions:
    collection_pct: float | None = None
    collection_weeks: int | None = None
    collection_haircut_pct: float | None = None
    deferral_weeks: int | None = None
    late_fee_pct: float | None = None
    discretionary_reduction_pct: float | None = None
    discretionary_start_week: int | None = None
    financing_template: str = "Term loan"
    financing_terms: FinancingTerms = field(default_factory=FinancingTerms)


@dataclass(frozen=True)
class BalancePoint:
    week: int
    week_start: str
    closing_balance: float
    layer: str


@dataclass(frozen=True)
class Plan:
    plan_id: str
    balance_series_before: tuple[BalancePoint, ...]
    balance_series_after: tuple[BalancePoint, ...]
    funding_gap: float
    remaining_gap: float
    shortage_week: int | None
    financing_amount: float
    financing_cost: float
    repayment_schedule: tuple[dict[str, float | int], ...]
    capacity_ratio: float | None
    capacity_label: str
    is_feasible: bool
    breach_probability: None
    risks: tuple[str, ...]
    assumptions_with_sources: tuple[dict[str, str | float | int], ...]
    pros: tuple[str, ...]
    cons: tuple[str, ...]
    next_steps: tuple[str, ...]
    layer_tags: tuple[str, ...] = ("HYPOTHETICAL",)
    unconfirmed_assumption_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible primitive values."""
        return asdict(self)


@dataclass(frozen=True)
class LabResult:
    plans: dict[str, Plan]
    best_plan_id: str
    best_plan_reason: str
    borrowing_necessary: bool
    borrowing_reason: str
    key_answers: dict[str, dict[str, str | float | bool | None]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plans": {name: plan.to_dict() for name, plan in self.plans.items()},
            "best_plan_id": self.best_plan_id,
            "best_plan_reason": self.best_plan_reason,
            "borrowing_necessary": self.borrowing_necessary,
            "borrowing_reason": self.borrowing_reason,
            "key_answers": self.key_answers,
        }


def _bounded(value: float, lower: float, upper: float, name: str) -> float:
    if not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{name} must be between {lower:g} and {upper:g}.")
    return value


def _resolved_assumptions(case: SyntheticCase, values: LabAssumptions) -> dict[str, float | int]:
    source = case.assumptions
    resolved: dict[str, float | int] = {
        "collection_pct": source.collection_pct if values.collection_pct is None else values.collection_pct,
        "collection_weeks": source.collection_weeks if values.collection_weeks is None else values.collection_weeks,
        "collection_haircut_pct": source.collection_haircut_pct if values.collection_haircut_pct is None else values.collection_haircut_pct,
        "deferral_weeks": source.deferral_weeks if values.deferral_weeks is None else values.deferral_weeks,
        "late_fee_pct": source.late_fee_pct if values.late_fee_pct is None else values.late_fee_pct,
        "discretionary_reduction_pct": source.discretionary_reduction_pct if values.discretionary_reduction_pct is None else values.discretionary_reduction_pct,
        "discretionary_start_week": source.discretionary_start_week if values.discretionary_start_week is None else values.discretionary_start_week,
    }
    _bounded(float(resolved["collection_pct"]), 0, 100, "Collection percentage")
    _bounded(float(resolved["collection_haircut_pct"]), 0, 100, "Collection haircut")
    _bounded(float(resolved["late_fee_pct"]), 0, 100, "Late fee percentage")
    _bounded(float(resolved["discretionary_reduction_pct"]), 0, 100, "Discretionary reduction")
    for key in ("collection_weeks", "deferral_weeks", "discretionary_start_week"):
        if int(resolved[key]) < 1:
            raise ValueError(f"{key.replace('_', ' ').capitalize()} must be at least 1.")
    return resolved


def _bucket(event_date: date, first_week: date) -> int:
    return max(0, (event_date - first_week).days // 7)


def _build_cash_series(
    case: SyntheticCase,
    projection: ForecastResult,
    assumptions: dict[str, float | int],
    active: set[str],
) -> tuple[list[float], list[float], list[str], list[dict[str, str | float | int]], list[str]]:
    weeks = projection.forecast_weeks
    inflows = [row.inflow for row in weeks]
    outflows = [row.outflow for row in weeks]
    first_week = weeks[0].week_start
    horizon = len(weeks)
    provenance: list[dict[str, str | float | int]] = []
    risks: list[str] = []
    collection_delta = [0.0] * horizon
    scheduled_bills: list[tuple[Any, int, float]] = []

    if "L1" in active:
        eligible = []
        as_of = first_week - timedelta(days=1)
        for invoice in case.receivables:
            outstanding = max(0.0, invoice.amount - invoice.paid_amount)
            if outstanding <= 0 or invoice.due_date > as_of:
                continue
            collectible = outstanding * float(assumptions["collection_pct"]) / 100
            collectible *= 1 - float(assumptions["collection_haircut_pct"]) / 100
            expected = invoice.due_date + timedelta(days=projection.payment_delay_days.get(invoice.customer_id, 0))
            eligible.append((invoice, collectible, _bucket(expected, first_week)))
        total = sum(item[1] for item in eligible)
        if total:
            weeks_to_collect = min(horizon, int(assumptions["collection_weeks"]))
            each_week = total / weeks_to_collect
            for index in range(weeks_to_collect):
                collection_delta[index] += each_week
            for invoice, collected, expected_index in eligible:
                if expected_index < horizon:
                    collection_delta[expected_index] -= collected
            provenance.append({"assumption": "L1 collections", "value": total,
                               "source": "Open receivables due before forecast start; configured collection %, timing and haircut"})
            risks.append("Collection timing and amount are hypothetical; customer payment is unconfirmed.")

    for bill in case.payables:
        outstanding = max(0.0, bill.amount - bill.paid_amount)
        if outstanding <= 0:
            continue
        original_index = _bucket(bill.due_date, first_week)
        shifted_index = original_index
        late_cost = 0.0
        if "L2" in active and bill.deferrable:
            shifted_index += int(assumptions["deferral_weeks"])
            late_cost = outstanding * float(assumptions["late_fee_pct"]) / 100
            if original_index < horizon:
                outflows[original_index] -= outstanding
            risks.append("Supplier agreement and any late charge are hypothetical; deferral may affect the relationship.")
        scheduled_bills.append((bill, shifted_index, outstanding))
        if "L2" in active and bill.deferrable:
            if shifted_index < horizon:
                outflows[shifted_index] += outstanding + late_cost
            provenance.append({"assumption": "L2 payable deferral", "value": int(assumptions["deferral_weeks"]),
                               "source": f"Deferrable bills in case data; late fee {assumptions['late_fee_pct']:g}%"})
            if shifted_index >= horizon:
                risks.append("Deferred payable falls beyond this forecast horizon and remains an outstanding obligation.")

    for index, amount in enumerate(collection_delta):
        inflows[index] += amount

    if "L3" in active:
        pct = float(assumptions["discretionary_reduction_pct"]) / 100
        from_week = int(assumptions["discretionary_start_week"])
        reduction_total = 0.0
        for bill, due_index, outstanding in scheduled_bills:
            if bill.discretionary and due_index < horizon and due_index + 1 >= from_week:
                reduction = outstanding * pct
                outflows[due_index] -= reduction
                reduction_total += reduction
        if reduction_total:
            provenance.append({"assumption": "L3 discretionary expense reduction", "value": reduction_total,
                               "source": f"Discretionary payables from week {from_week}; configured reduction percentage"})
            risks.append("Expense reductions may disrupt operations; the selected spend is not verified as avoidable.")

    # Enforce non-negative event buckets within floating-point tolerance.
    outflows = [max(0.0, value) if value > -1e-8 else value for value in outflows]
    return inflows, outflows, [row.week_start.isoformat() for row in weeks], provenance, list(dict.fromkeys(risks))


def _make_plan(
    name: str,
    base_projection: ForecastResult,
    inflows: list[float],
    outflows: list[float],
    dates: list[str],
    provenance: list[dict[str, str | float | int]],
    risks: list[str],
    financing_template: str,
    financing_terms: FinancingTerms,
    *,
    finance: bool,
) -> Plan:
    reserve = base_projection.reserve
    before = tuple(BalancePoint(i + 1, day, row.closing_balance, "FORECAST")
                   for i, (day, row) in enumerate(zip(dates, base_projection.forecast_weeks)))
    running = base_projection.opening_cash
    lever_balances: list[float] = []
    for inflow, outflow in zip(inflows, outflows):
        running += inflow - outflow
        lever_balances.append(running)
    lever_gap = max(0.0, reserve - min(lever_balances, default=running))
    finance_result = None
    amount = cost = 0.0
    ratio = None
    label = "No repayment"
    schedule: tuple[dict[str, float | int], ...] = ()
    after_balances = lever_balances.copy()
    if finance:
        adjusted_weeks = [replace(row, inflow=inflow, outflow=outflow, net=inflow - outflow)
                          for row, inflow, outflow in zip(base_projection.forecast_weeks, inflows, outflows)]
        adjusted_projection = replace(base_projection, forecast_weeks=adjusted_weeks)
        finance_result = calculate_financing(financing_template, lever_gap, financing_terms, adjusted_projection)
        amount = finance_result.amount
        cost = finance_result.total_cost
        ratio = finance_result.capacity_ratio
        label = finance_result.pressure_label
        schedule = tuple(asdict(payment) for payment in finance_result.schedule)
        net_proceeds = amount * financing_terms.advance_pct / 100 if financing_template == "Invoice financing" else amount
        if after_balances:
            after_balances[0] += net_proceeds
        for payment in finance_result.schedule:
            week_index = payment.month * 4 - 1
            if week_index < len(after_balances):
                after_balances[week_index] -= payment.payment
        risks.extend(finance_result.risk_notes)

    shortage = next((i + 1 for i, value in enumerate(after_balances) if value < reserve), None)
    remaining_gap = max(0.0, reserve - min(after_balances, default=running))
    feasible = remaining_gap <= 1e-7
    after = tuple(BalancePoint(i + 1, day, balance, "HYPOTHETICAL" if finance or name != "Option 0" else "FORECAST")
                  for i, (day, balance) in enumerate(zip(dates, after_balances)))
    if finance_result:
        risks = list(dict.fromkeys([*risks, *finance_result.risk_notes]))
    if feasible:
        pros = ("Projected closing balances stay at or above the minimum reserve within the forecast horizon.",)
        cons = tuple(risks) or ("Levers still depend on unconfirmed assumptions.",)
        next_steps = ("Review the assumptions and confirm any proposed action before treating it as committed.",)
    else:
        pros = (f"Reduces the projected reserve shortfall; remaining gap is BDT {remaining_gap:,.0f}.",)
        cons = tuple(risks) or ("The projected reserve is not maintained throughout the forecast horizon.",)
        next_steps = ("Review the remaining shortfall and test other assumptions; this plan does not fully maintain reserve.",)
    assumption_count = len(provenance) + (1 if finance and amount > 0 else 0)
    return Plan(
        name, before, after, lever_gap, remaining_gap, shortage, amount, cost, schedule,
        ratio, label, feasible, None, tuple(dict.fromkeys(risks)), tuple(provenance), pros, cons,
        next_steps, ("HYPOTHETICAL",), assumption_count,
    )


def _pressure_rank(label: str) -> int:
    return {"No repayment": 0, "Comfortable": 1, "Tight": 2, "Stressed": 3}.get(label, 4)


def run_lab(case: SyntheticCase, assumptions: LabAssumptions | None = None) -> LabResult:
    """Compare baseline, isolated levers, combined levers and financing choices."""
    settings = assumptions or LabAssumptions()
    if settings.financing_template not in TEMPLATES:
        raise ValueError("Unknown financing template.")
    resolved = _resolved_assumptions(case, settings)
    projection = forecast(case)
    base_in = [week.inflow for week in projection.forecast_weeks]
    base_out = [week.outflow for week in projection.forecast_weeks]
    dates = [week.week_start.isoformat() for week in projection.forecast_weeks]
    source_base: list[dict[str, str | float | int]] = [
        {"assumption": "Minimum reserve", "value": projection.reserve,
         "source": "Forecast result derived from configured reserve weeks and recent fixed outflows"},
        {"assumption": "Baseline forecast", "value": len(projection.forecast_weeks),
         "source": "Deterministic core.forecast forecast weeks"},
    ]
    plans: dict[str, Plan] = {}
    plans["Option 0"] = _make_plan("Option 0", projection, base_in, base_out, dates,
                                   list(source_base), [], settings.financing_template, settings.financing_terms, finance=False)
    for lever in ("L1", "L2", "L3"):
        ins, outs, week_dates, provenance, risks = _build_cash_series(case, projection, resolved, {lever})
        plans[lever] = _make_plan(lever, projection, ins, outs, week_dates, [*source_base, *provenance], risks,
                                  settings.financing_template, settings.financing_terms, finance=False)

    ins, outs, week_dates, provenance, risks = _build_cash_series(case, projection, resolved, {"L1", "L2", "L3"})
    plans["Option A"] = _make_plan("Option A", projection, ins, outs, week_dates, [*source_base, *provenance], risks,
                                   settings.financing_template, settings.financing_terms, finance=False)
    # Option B finances only the combined levers' remaining gap. Financing proceeds
    # are net of the invoice-financing advance rate; principal/charges follow schedule.
    plans["Option B"] = _make_plan("Option B", projection, ins, outs, week_dates, [*source_base, *provenance], list(risks),
                                   settings.financing_template, settings.financing_terms, finance=True)
    plans["Option C"] = _make_plan("Option C", projection, base_in, base_out, dates, list(source_base), [],
                                   settings.financing_template, settings.financing_terms, finance=True)

    candidates = [plans[key] for key in ("Option 0", "Option A", "Option B", "Option C")]
    feasible = [plan for plan in candidates if plan.is_feasible]
    if feasible:
        selected = min(feasible, key=lambda plan: (plan.financing_cost, _pressure_rank(plan.capacity_label),
                                                    plan.unconfirmed_assumption_count))
        reason = (f"{selected.plan_id} is feasible on the deterministic forecast and has the lowest modelled cost "
                  "after repayment-pressure and unconfirmed-assumption tie-breaks.")
    else:
        selected = min(candidates, key=lambda plan: (plan.remaining_gap, plan.financing_cost,
                                                      _pressure_rank(plan.capacity_label), plan.unconfirmed_assumption_count))
        reason = (f"No plan fully closes the gap; {selected.plan_id} has the smallest remaining reserve gap "
                  f"(BDT {selected.remaining_gap:,.0f}).")

    no_borrow_gap = plans["Option A"].remaining_gap
    borrowing_necessary = no_borrow_gap > 1e-7
    if not borrowing_necessary:
        borrowing_reason = "The combined non-financing levers maintain the reserve in this deterministic forecast."
    elif feasible and selected.financing_amount > 0:
        borrowing_reason = f"Option A leaves a BDT {no_borrow_gap:,.0f} gap; a feasible selected plan includes illustrative financing."
    else:
        borrowing_reason = f"Option A leaves a BDT {no_borrow_gap:,.0f} gap, but no candidate fully maintains reserve; financing alone is not sufficient under these inputs."

    best = plans[selected.plan_id]
    key_answers: dict[str, dict[str, str | float | bool | None]] = {
        "funding_gap": {"question": "How large is the original projected funding gap?", "answer": projection.funding_gap},
        "shortage_timing": {"question": "When does the baseline first breach reserve?", "answer": projection.shortage_week},
        "best_plan": {"question": "Which candidate is best under the stated rule?", "answer": selected.plan_id},
        "borrowing_necessary": {"question": "Is borrowing necessary in this model?", "answer": borrowing_necessary},
        "main_risk": {"question": "What should be checked before acting?", "answer": best.risks[0] if best.risks else "No plan-specific risk flag; validate the source data and assumptions."},
    }
    # Probability is intentionally unavailable until the later uncertainty task;
    # each plan exposes null instead of implying a computed probability.
    return LabResult(plans, selected.plan_id, reason, borrowing_necessary, borrowing_reason, key_answers)
