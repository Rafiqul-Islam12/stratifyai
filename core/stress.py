"""Deterministic input shocks for sales, operating costs, collections and FX."""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import timedelta

from core.loaders import SyntheticCase


@dataclass(frozen=True)
class StressInputs:
    sales_drop_pct: float = 0.0
    cost_increase_pct: float = 0.0
    customer_delay_days: int = 0
    fx_shock_pct: float = 0.0


@dataclass(frozen=True)
class StressResult:
    case: SyntheticCase
    inputs: StressInputs
    assumptions: tuple[dict[str, str | float | int], ...]
    risk_notes: tuple[str, ...]


def _validate(inputs: StressInputs) -> None:
    for value, low, high, label in (
        (inputs.sales_drop_pct, 0, 100, "Sales decrease"),
        (inputs.cost_increase_pct, 0, 200, "Cost increase"),
        (inputs.fx_shock_pct, -100, 200, "FX shock"),
    ):
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{label} must be between {low} and {high} percent.")
    if not isinstance(inputs.customer_delay_days, int) or not 0 <= inputs.customer_delay_days <= 365:
        raise ValueError("Customer delay must be between 0 and 365 whole days.")


def _fx_exposed(category: str, *, import_case: bool) -> bool:
    normalized = category.casefold()
    keywords = ("import", "shipping", "freight", "duty", "customs", "inventory")
    return any(word in normalized for word in keywords) and import_case


def apply_stress(case: SyntheticCase, inputs: StressInputs) -> StressResult:
    """Return a copied case with explicit hypothetical shocks applied.

    Existing balances and paid amounts stay fixed. Sales shocks reduce only open
    invoice balances and historical sales rates used as a forecast proxy; cost
    shocks affect projected operating outflows and unpaid bills. FX is applied
    only to import-linked categories when the case contains import assumptions.
    """
    _validate(inputs)
    sales_factor = 1 - inputs.sales_drop_pct / 100
    cost_factor = 1 + inputs.cost_increase_pct / 100
    import_case = bool(case.profile.import_scenario)
    fx_factor = 1 + inputs.fx_shock_pct / 100
    transactions = [
        tx.model_copy(update={
            "amount": tx.amount * (sales_factor if tx.direction == "inflow" else
                                   cost_factor * (fx_factor if _fx_exposed(tx.category, import_case=import_case) else 1)),
        })
        for tx in case.transactions
    ]
    receivables = [
        row.model_copy(update={
            "amount": row.paid_amount + max(0.0, row.amount - row.paid_amount) * sales_factor,
            "due_date": row.due_date + timedelta(days=inputs.customer_delay_days)
            if row.paid_amount < row.amount else row.due_date,
        })
        for row in case.receivables
    ]
    payables = [
        row.model_copy(update={
            "amount": row.paid_amount + max(0.0, row.amount - row.paid_amount) * cost_factor
            * (fx_factor if _fx_exposed(row.category, import_case=import_case) else 1),
        })
        for row in case.payables
    ]
    transformed = replace(case, transactions=transactions, receivables=receivables, payables=payables)
    assumptions = (
        {"assumption": "Sales decrease (%)", "value": inputs.sales_drop_pct, "source": "Editable stress input"},
        {"assumption": "Operating cost increase (%)", "value": inputs.cost_increase_pct, "source": "Editable stress input; applied to projected operating outflows"},
        {"assumption": "Additional customer delay (days)", "value": inputs.customer_delay_days, "source": "Editable stress input; shifts open invoice due dates"},
        {"assumption": "FX shock (%)", "value": inputs.fx_shock_pct, "source": "Editable stress input; applied to import-linked categories only"},
    )
    notes = ["Stress results are hypothetical; input shocks are not predictions."]
    if inputs.fx_shock_pct and not import_case:
        notes.append("No import-linked profile is present, so the FX shock does not change this case's amounts.")
    return StressResult(transformed, inputs, assumptions, tuple(notes))
