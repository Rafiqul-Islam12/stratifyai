"""Per-case, session-local validated assumptions shared by Lab and settings pages."""
from __future__ import annotations

from typing import Any

import streamlit as st

from core.financing import FinancingTerms
from core.forecast import forecast
from core.import_scenario import default_import_inputs
from core.lab import LabAssumptions
from core.loaders import SyntheticCase
from core.stress import StressInputs

STORE_KEY = "stratify_assumptions_by_case"
FINANCING_DEFAULTS = {
    "Term loan": (14.0, 1.0, 6, 80.0),
    "Invoice financing": (0.0, 2.0, 1, 80.0),
    "Supplier credit": (0.0, 1.5, 1, 80.0),
    "Credit line": (16.0, 0.5, 6, 80.0),
}
RANGES: dict[str, tuple[float, float]] = {
    "reserve_bdt": (0, 100_000_000), "reserve_weeks": (0, 52), "horizon_weeks": (8, 13),
    "funding_buffer_pct": (0, 100), "collection_pct": (0, 100), "collection_weeks": (1, 52),
    "sales_variability_cv": (0, 2), "customer_delay_sd_days": (0, 180),
    "collection_haircut_pct": (0, 100), "deferral_weeks": (1, 52), "late_fee_pct": (0, 100),
    "discretionary_reduction_pct": (0, 100), "discretionary_start_week": (1, 52),
    "annual_rate_pct": (0, 100), "fee_pct": (0, 100), "tenor_months": (1, 120), "advance_pct": (1, 100),
    "stress_sales_drop_pct": (0, 100), "stress_cost_increase_pct": (0, 200),
    "stress_delay_days": (0, 365), "stress_fx_shock_pct": (-100, 200),
    "import_product_cost_foreign": (0, 1_000_000_000), "import_deposit_pct": (0, 100),
    "import_shipping_cost_foreign": (0, 1_000_000_000), "import_duties_taxes_pct": (0, 100),
    "import_fx_rate": (0.000001, 100_000), "import_fx_shock_pct": (-100, 200),
    "import_lead_time_weeks": (1, 52), "import_sales_ramp_weeks": (1, 52),
    "import_collection_delay_days": (0, 365),
}


def defaults_for_case(case: SyntheticCase) -> dict[str, Any]:
    """Build user-editable defaults from the selected synthetic case."""
    assumptions = case.assumptions
    projection = forecast(case)
    rate, fee, tenor, advance = FINANCING_DEFAULTS["Term loan"]
    imported = default_import_inputs(case)
    return {
        "reserve_mode": "Reserve weeks",
        "reserve_bdt": round(projection.reserve),
        "reserve_weeks": assumptions.minimum_reserve_weeks,
        "horizon_weeks": assumptions.forecast_horizon_weeks,
        "funding_buffer_pct": assumptions.funding_buffer_pct,
        "sales_variability_cv": assumptions.sales_variability_cv,
        "customer_delay_sd_days": assumptions.customer_delay_sd_days,
        "collection_pct": assumptions.collection_pct,
        "collection_weeks": assumptions.collection_weeks,
        "collection_haircut_pct": assumptions.collection_haircut_pct,
        "deferral_weeks": assumptions.deferral_weeks,
        "late_fee_pct": assumptions.late_fee_pct,
        "discretionary_reduction_pct": assumptions.discretionary_reduction_pct,
        "discretionary_start_week": assumptions.discretionary_start_week,
        "financing_template": "Term loan",
        "annual_rate_pct": rate, "fee_pct": fee, "tenor_months": tenor, "advance_pct": advance,
        "stress_sales_drop_pct": 0.0, "stress_cost_increase_pct": 0.0,
        "stress_delay_days": 0, "stress_fx_shock_pct": 0.0,
        "include_import_scenario": bool(case.profile.import_scenario),
        "import_product_cost_foreign": imported.product_cost_foreign,
        "import_deposit_pct": imported.deposit_pct,
        "import_shipping_cost_foreign": imported.shipping_cost_foreign,
        "import_duties_taxes_pct": imported.duties_taxes_pct,
        "import_fx_rate": imported.fx_rate_bdt_per_unit,
        "import_fx_shock_pct": imported.fx_shock_pct,
        "import_lead_time_weeks": imported.lead_time_weeks,
        "import_sales_ramp_weeks": imported.sales_ramp_weeks,
        "import_collection_delay_days": imported.collection_delay_days,
    }


def get_values(case_name: str, case: SyntheticCase) -> dict[str, Any]:
    state = st.session_state.setdefault(STORE_KEY, {})
    if case_name not in state:
        state[case_name] = defaults_for_case(case)
    return {**defaults_for_case(case), **state[case_name]}


def validate_values(values: dict[str, Any]) -> dict[str, Any]:
    checked = dict(values)
    for name, (low, high) in RANGES.items():
        if name not in checked:
            continue
        value = checked[name]
        if isinstance(value, bool) or not low <= float(value) <= high:
            raise ValueError(f"{name.replace('_', ' ').capitalize()} must be between {low:g} and {high:g}.")
        if name in {
            "horizon_weeks", "collection_weeks", "deferral_weeks", "discretionary_start_week",
            "tenor_months", "stress_delay_days", "import_lead_time_weeks", "import_sales_ramp_weeks",
            "import_collection_delay_days",
        } and float(value) != int(value):
            raise ValueError(f"{name.replace('_', ' ').capitalize()} must be a whole number.")
        checked[name] = int(value) if name in {
            "horizon_weeks", "collection_weeks", "deferral_weeks", "discretionary_start_week",
            "tenor_months", "stress_delay_days", "import_lead_time_weeks", "import_sales_ramp_weeks",
            "import_collection_delay_days",
        } else float(value)
    if checked.get("financing_template") not in FINANCING_DEFAULTS:
        raise ValueError("Choose one of the four financing templates.")
    if checked.get("reserve_mode") not in ("Reserve weeks", "Fixed BDT"):
        raise ValueError("Choose reserve weeks or a fixed BDT amount.")
    if not isinstance(checked.get("include_import_scenario"), bool):
        raise TypeError("Import scenario toggle must be true or false.")
    return checked


def save_values(case_name: str, values: dict[str, Any]) -> dict[str, Any]:
    checked = validate_values(values)
    st.session_state.setdefault(STORE_KEY, {})[case_name] = checked
    return checked


def reset_values(case_name: str, case: SyntheticCase) -> dict[str, Any]:
    checked = defaults_for_case(case)
    st.session_state.setdefault(STORE_KEY, {})[case_name] = checked
    return checked


def to_lab_assumptions(values: dict[str, Any]) -> LabAssumptions:
    settings = validate_values(values)
    return LabAssumptions(
        reserve=float(settings["reserve_bdt"]) if settings["reserve_mode"] == "Fixed BDT" else None,
        reserve_weeks=float(settings["reserve_weeks"]),
        funding_buffer_pct=float(settings["funding_buffer_pct"]),
        horizon_weeks=int(settings["horizon_weeks"]),
        sales_variability_cv=float(settings["sales_variability_cv"]),
        customer_delay_sd_days=float(settings["customer_delay_sd_days"]),
        collection_pct=float(settings["collection_pct"]),
        collection_weeks=int(settings["collection_weeks"]),
        collection_haircut_pct=float(settings["collection_haircut_pct"]),
        deferral_weeks=int(settings["deferral_weeks"]),
        late_fee_pct=float(settings["late_fee_pct"]),
        discretionary_reduction_pct=float(settings["discretionary_reduction_pct"]),
        discretionary_start_week=int(settings["discretionary_start_week"]),
        financing_template=settings["financing_template"],
        financing_terms=FinancingTerms(
            float(settings["annual_rate_pct"]), float(settings["fee_pct"]),
            int(settings["tenor_months"]), float(settings["advance_pct"]),
        ),
    )


def to_stress_inputs(values: dict[str, Any]) -> StressInputs:
    settings = validate_values(values)
    return StressInputs(
        float(settings["stress_sales_drop_pct"]), float(settings["stress_cost_increase_pct"]),
        int(settings["stress_delay_days"]), float(settings["stress_fx_shock_pct"]),
    )
