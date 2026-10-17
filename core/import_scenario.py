"""Editable, hypothetical import cash-flow events for the synthetic case 4."""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import timedelta

from core.forecast import forecast
from core.loaders import SyntheticCase
from core.schema import Customer, Payable, Receivable


@dataclass(frozen=True)
class ImportInputs:
    product_cost_foreign: float
    deposit_pct: float
    shipping_cost_foreign: float
    duties_taxes_pct: float
    fx_rate_bdt_per_unit: float
    fx_shock_pct: float
    lead_time_weeks: int
    sales_ramp_weeks: int
    collection_delay_days: int


@dataclass(frozen=True)
class ImportCashEvent:
    week: int
    date: str
    event: str
    amount_bdt: float
    layer: str = "HYPOTHETICAL"


@dataclass(frozen=True)
class ImportScenarioResult:
    scenario_case: SyntheticCase
    inputs: ImportInputs
    base_fx_rate: float
    shocked_fx_rate: float
    product_cost_bdt: float
    shipping_cost_bdt: float
    duties_taxes_bdt: float
    deposit_bdt: float
    landed_cost_bdt: float
    estimated_weekly_sales_bdt: float
    events: tuple[ImportCashEvent, ...]
    assumptions_with_sources: tuple[dict[str, str | float | int], ...]
    risk_notes: tuple[str, ...]


def default_import_inputs(case: SyntheticCase) -> ImportInputs:
    """Translate case 4's BDT cost defaults to foreign-unit inputs at its base FX."""
    data = case.profile.import_scenario
    base_fx = float(data.get("fx_rate_bdt_per_usd", 122.0))
    if base_fx <= 0:
        base_fx = 122.0
    return ImportInputs(
        product_cost_foreign=float(data.get("product_cost", 0.0)) / base_fx,
        deposit_pct=float(data.get("deposit_pct", 30.0)),
        shipping_cost_foreign=float(data.get("shipping_cost", 0.0)) / base_fx,
        duties_taxes_pct=float(data.get("duties_taxes_pct", 0.0)),
        fx_rate_bdt_per_unit=base_fx,
        fx_shock_pct=0.0,
        lead_time_weeks=int(data.get("lead_time_weeks", 8)),
        sales_ramp_weeks=int(data.get("sales_ramp_weeks", 10)),
        collection_delay_days=int(sum(c.typical_delay_days for c in case.profile.customers) / max(1, len(case.profile.customers))),
    )


def _validate(inputs: ImportInputs) -> None:
    for value, low, high, label in (
        (inputs.product_cost_foreign, 0, 1_000_000_000, "Product cost"),
        (inputs.shipping_cost_foreign, 0, 1_000_000_000, "Shipping cost"),
        (inputs.deposit_pct, 0, 100, "Deposit percentage"),
        (inputs.duties_taxes_pct, 0, 100, "Duties and taxes percentage"),
        (inputs.fx_rate_bdt_per_unit, 0.000001, 100_000, "FX rate"),
        (inputs.fx_shock_pct, -100, 200, "FX shock"),
    ):
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{label} must be between {low:g} and {high:g}.")
    for value, label in ((inputs.lead_time_weeks, "Lead time"), (inputs.sales_ramp_weeks, "Sales ramp")):
        if not isinstance(value, int) or not 1 <= value <= 52:
            raise ValueError(f"{label} must be between 1 and 52 whole weeks.")
    if not isinstance(inputs.collection_delay_days, int) or not 0 <= inputs.collection_delay_days <= 365:
        raise ValueError("Collection delay must be between 0 and 365 whole days.")


def build_import_scenario(case: SyntheticCase, inputs: ImportInputs) -> ImportScenarioResult:
    """Create hypothetical deposit, landed-cost, and collection events.

    Product and shipping inputs are in foreign currency units and converted at
    the editable BDT FX rate. Duties/taxes are a user-entered percentage with no
    country-specific rate or eligibility assumption.
    """
    _validate(inputs)
    source = case.profile.import_scenario
    base_fx = float(source.get("fx_rate_bdt_per_usd", inputs.fx_rate_bdt_per_unit))
    shocked_fx = inputs.fx_rate_bdt_per_unit * (1 + inputs.fx_shock_pct / 100)
    product_bdt = inputs.product_cost_foreign * shocked_fx
    shipping_bdt = inputs.shipping_cost_foreign * shocked_fx
    duty_bdt = (product_bdt + shipping_bdt) * inputs.duties_taxes_pct / 100
    deposit = product_bdt * inputs.deposit_pct / 100
    landed = product_bdt + shipping_bdt + duty_bdt
    projection = forecast(case)
    first_week = projection.forecast_weeks[0].week_start
    arrival_date = first_week + timedelta(weeks=inputs.lead_time_weeks - 1)
    deposit_id = "HYP-IMPORT-DEPOSIT"
    arrival_id = "HYP-IMPORT-LANDED"
    supplier_id = case.profile.suppliers[0].supplier_id if case.profile.suppliers else "HYP-SUPPLIER"
    new_payables = []
    if deposit > 0.01:
        new_payables.append(Payable(bill_id=deposit_id, supplier_id=supplier_id,
                                    issue_date=first_week, due_date=first_week, amount=deposit,
                                    category="Hypothetical import deposit"))
    if landed - deposit > 0.01:
        new_payables.append(Payable(
            bill_id=arrival_id, supplier_id=supplier_id,
            issue_date=arrival_date, due_date=arrival_date, amount=landed - deposit,
            category="Hypothetical import landed cost",
        ))

    recent_sales = [week.inflow for week in projection.actual_weeks[-8:]]
    weekly_sales = sum(recent_sales) / len(recent_sales) if recent_sales else 0.0
    customer_id = "HYP-IMPORT-SALES"
    customer = Customer(customer_id=customer_id, name="Hypothetical import sales", typical_delay_days=inputs.collection_delay_days)
    updated_profile = case.profile.model_copy(update={
        "customers": [*case.profile.customers, customer],
        "import_scenario": {
            **source,
            "fx_rate_bdt_per_usd": inputs.fx_rate_bdt_per_unit,
            "fx_shock_pct": inputs.fx_shock_pct,
            "lead_time_weeks": inputs.lead_time_weeks,
        },
    })
    new_receivables: list[Receivable] = []
    events: list[ImportCashEvent] = []
    if deposit > 0:
        events.append(ImportCashEvent(1, first_week.isoformat(), "Import deposit", deposit))
    arrival_week = inputs.lead_time_weeks
    events.append(ImportCashEvent(arrival_week, arrival_date.isoformat(), "Remaining product, shipping and duties/taxes", landed - deposit))
    for index in range(inputs.sales_ramp_weeks):
        sale_week = inputs.lead_time_weeks + index + 1
        ramp_share = (index + 1) / inputs.sales_ramp_weeks
        sale_amount = weekly_sales * ramp_share
        sale_date = first_week + timedelta(weeks=sale_week - 1)
        collection_date = sale_date + timedelta(days=inputs.collection_delay_days)
        if sale_amount > 0:
            new_receivables.append(Receivable(
                invoice_id=f"HYP-IMPORT-SALE-{index + 1:02d}", customer_id=customer_id,
                issue_date=sale_date, due_date=sale_date, amount=sale_amount,
            ))
            collection_week = max(1, (collection_date - first_week).days // 7 + 1)
            events.append(ImportCashEvent(collection_week, collection_date.isoformat(), "Hypothetical sales collection", sale_amount))

    scenario_case = replace(case, profile=updated_profile,
                            receivables=[*case.receivables, *new_receivables],
                            payables=[*case.payables, *new_payables])
    assumptions = (
        {"assumption": "Product cost (foreign units)", "value": inputs.product_cost_foreign, "source": "Editable import assumption from case 4 profile"},
        {"assumption": "Shipping cost (foreign units)", "value": inputs.shipping_cost_foreign, "source": "Editable import assumption from case 4 profile"},
        {"assumption": "FX rate (BDT per unit)", "value": inputs.fx_rate_bdt_per_unit, "source": "Editable user assumption; no country rule inferred"},
        {"assumption": "FX shock (%)", "value": inputs.fx_shock_pct, "source": "Editable stress assumption"},
        {"assumption": "Deposit percentage", "value": inputs.deposit_pct, "source": "Editable user assumption"},
        {"assumption": "Duties and taxes (%)", "value": inputs.duties_taxes_pct, "source": "Editable user assumption; not a country rate"},
        {"assumption": "Lead time (weeks)", "value": inputs.lead_time_weeks, "source": "Editable user assumption"},
        {"assumption": "Sales ramp (weeks)", "value": inputs.sales_ramp_weeks, "source": "Editable user assumption; revenue uses recent actual weekly sales"},
        {"assumption": "Collection delay (days)", "value": inputs.collection_delay_days, "source": "Editable user assumption"},
    )
    return ImportScenarioResult(scenario_case, inputs, base_fx, shocked_fx, product_bdt, shipping_bdt, duty_bdt,
                               deposit, landed, weekly_sales, tuple(sorted(events, key=lambda event: (event.week, event.event))),
                               assumptions,
                               ("Import cash events and sales receipts are HYPOTHETICAL; shipping, duties/taxes and timing require confirmation.",))
