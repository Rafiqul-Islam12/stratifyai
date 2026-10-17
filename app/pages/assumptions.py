"""Validated per-case assumption store shared with the Decision Lab."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app import components as ui
from app.assumptions_store import get_values, reset_values, save_values
from core.loaders import load_case
from data.generate_synthetic import CASES

CASE_LABELS = {
    "stable_healthy": "Stable and healthy", "delayed_customer_payments": "Delayed customer payments",
    "high_expense_shortage": "High expense, shortage", "import_financing": "Import financing",
    "sales_drop_cost_rise": "Sales drop, cost rise",
}


def _key(case_name: str, name: str) -> str:
    return f"assumptions::{case_name}::{name}"

ui.load_styles()
active = st.session_state.get("active_synthetic_case", "high_expense_shortage")
case_name = st.selectbox("Synthetic demo case", CASES,
                         index=CASES.index(active) if active in CASES else CASES.index("high_expense_shortage"),
                         format_func=lambda value: CASE_LABELS[value], key="assumptions-case-select")
case = load_case(case_name)
st.session_state["active_synthetic_case"] = case_name
st.session_state["synthetic_case_data"] = case
values = get_values(case_name, case)
ui.page_header("Assumptions", "Edit and review the values shared by forecasts, Lab levers and illustrative financing.",
               business=case.profile.business_name, scenario=CASE_LABELS[case_name])
ui.alert_banner("warning", "Editable modelling assumptions",
                "Values are synthetic starting points and remain hypothetical. Financing terms are templates, not real offers.")
prefix = f"assumptions::{case_name}::"
if st.button("Reset this case to defaults", key=f"assumptions-reset-{case_name}"):
    for state_key in list(st.session_state):
        if state_key.startswith(prefix):
            del st.session_state[state_key]
    reset_values(case_name, case)
    st.rerun()

updates = dict(values)
ui.section_title("Forecast")
columns = st.columns(4)
updates["reserve_bdt"] = columns[0].number_input("Minimum reserve (BDT)", min_value=0, max_value=100_000_000,
    step=10_000, value=int(values["reserve_bdt"]), key=_key(case_name, "reserve_bdt"))
updates["reserve_weeks"] = columns[1].slider("Reserve basis (weeks)", 0.0, 13.0,
    float(values["reserve_weeks"]), step=0.5, key=_key(case_name, "reserve_weeks"))
updates["horizon_weeks"] = columns[2].slider("Forecast horizon (weeks)", 8, 13,
    int(values["horizon_weeks"]), key=_key(case_name, "horizon_weeks"))
updates["funding_buffer_pct"] = columns[3].slider("Funding gap buffer (%)", 0.0, 50.0,
    float(values["funding_buffer_pct"]), step=1.0, key=_key(case_name, "funding_buffer_pct"))

ui.section_title("Decision Lab levers")
columns = st.columns(4)
updates["collection_pct"] = columns[0].slider("L1 collection (%)", 0, 100, int(values["collection_pct"]), key=_key(case_name, "collection_pct"))
updates["collection_weeks"] = columns[1].slider("L1 timing (weeks)", 1, 13, int(values["collection_weeks"]), key=_key(case_name, "collection_weeks"))
updates["collection_haircut_pct"] = columns[2].slider("L1 haircut (%)", 0, 100, int(values["collection_haircut_pct"]), key=_key(case_name, "collection_haircut_pct"))
updates["deferral_weeks"] = columns[3].slider("L2 defer (weeks)", 1, 8, int(values["deferral_weeks"]), key=_key(case_name, "deferral_weeks"))
columns = st.columns(3)
updates["late_fee_pct"] = columns[0].slider("L2 late fee (%)", 0.0, 25.0, float(values["late_fee_pct"]), step=0.25, key=_key(case_name, "late_fee_pct"))
updates["discretionary_reduction_pct"] = columns[1].slider("L3 expense reduction (%)", 0, 80, int(values["discretionary_reduction_pct"]), key=_key(case_name, "discretionary_reduction_pct"))
updates["discretionary_start_week"] = columns[2].slider("L3 starts in week", 1, 13, int(values["discretionary_start_week"]), key=_key(case_name, "discretionary_start_week"))

ui.section_title("Financing template")
columns = st.columns(4)
templates = list({"Term loan": None, "Invoice financing": None, "Supplier credit": None, "Credit line": None})
updates["financing_template"] = columns[0].selectbox("Template", templates,
    index=templates.index(values["financing_template"]), key=_key(case_name, "financing_template"))
updates["annual_rate_pct"] = columns[1].number_input("Annual rate (%)", min_value=0.0, max_value=100.0,
    value=float(values["annual_rate_pct"]), step=0.5, key=_key(case_name, "annual_rate_pct"))
updates["fee_pct"] = columns[2].number_input("Fee / charge (%)", min_value=0.0, max_value=100.0,
    value=float(values["fee_pct"]), step=0.25, key=_key(case_name, "fee_pct"))
updates["tenor_months"] = columns[3].number_input("Tenor (months)", min_value=1, max_value=120,
    value=int(values["tenor_months"]), step=1, key=_key(case_name, "tenor_months"))
updates["advance_pct"] = st.slider("Invoice advance rate (%)", 1.0, 100.0, float(values["advance_pct"]),
    step=1.0, key=_key(case_name, "advance_pct"))

ui.section_title("Stress inputs")
columns = st.columns(4)
updates["stress_sales_drop_pct"] = columns[0].slider("Sales decrease (%)", 0.0, 50.0,
    float(values["stress_sales_drop_pct"]), step=1.0, key=_key(case_name, "stress_sales_drop_pct"))
updates["stress_cost_increase_pct"] = columns[1].slider("Operating cost increase (%)", 0.0, 100.0,
    float(values["stress_cost_increase_pct"]), step=1.0, key=_key(case_name, "stress_cost_increase_pct"))
updates["stress_delay_days"] = columns[2].slider("Additional customer delay (days)", 0, 180,
    int(values["stress_delay_days"]), key=_key(case_name, "stress_delay_days"))
updates["stress_fx_shock_pct"] = columns[3].slider("FX shock (%)", -50.0, 100.0,
    float(values["stress_fx_shock_pct"]), step=1.0, key=_key(case_name, "stress_fx_shock_pct"))

if case.profile.import_scenario:
    ui.section_title("Case 4 import scenario")
    updates["include_import_scenario"] = st.checkbox("Include hypothetical import shipment", bool(values["include_import_scenario"]), key=_key(case_name, "include_import_scenario"))
    columns = st.columns(4)
    updates["import_product_cost_foreign"] = columns[0].number_input("Product cost (foreign units)", min_value=0.0, max_value=1_000_000_000.0,
        value=float(values["import_product_cost_foreign"]), step=100.0, key=_key(case_name, "import_product_cost_foreign"))
    updates["import_deposit_pct"] = columns[1].slider("Deposit (%)", 0.0, 100.0,
        float(values["import_deposit_pct"]), step=1.0, key=_key(case_name, "import_deposit_pct"))
    updates["import_shipping_cost_foreign"] = columns[2].number_input("Shipping (foreign units)", min_value=0.0, max_value=1_000_000_000.0,
        value=float(values["import_shipping_cost_foreign"]), step=100.0, key=_key(case_name, "import_shipping_cost_foreign"))
    updates["import_duties_taxes_pct"] = columns[3].slider("Duties / taxes assumption (%)", 0.0, 100.0,
        float(values["import_duties_taxes_pct"]), step=0.5, key=_key(case_name, "import_duties_taxes_pct"))
    columns = st.columns(4)
    updates["import_fx_rate"] = columns[0].number_input("FX rate (BDT per unit)", min_value=0.000001, max_value=100_000.0,
        value=float(values["import_fx_rate"]), step=1.0, key=_key(case_name, "import_fx_rate"))
    updates["import_fx_shock_pct"] = columns[1].slider("Import FX shock (%)", -100.0, 200.0,
        float(values["import_fx_shock_pct"]), step=1.0, key=_key(case_name, "import_fx_shock_pct"))
    updates["import_lead_time_weeks"] = columns[2].number_input("Lead time (weeks)", min_value=1, max_value=52,
        value=int(values["import_lead_time_weeks"]), key=_key(case_name, "import_lead_time_weeks"))
    updates["import_sales_ramp_weeks"] = columns[3].number_input("Sales ramp (weeks)", min_value=1, max_value=52,
        value=int(values["import_sales_ramp_weeks"]), key=_key(case_name, "import_sales_ramp_weeks"))
    updates["import_collection_delay_days"] = st.number_input("Sales collection delay (days)", min_value=0, max_value=365,
        value=int(values["import_collection_delay_days"]), key=_key(case_name, "import_collection_delay_days"))
else:
    updates["include_import_scenario"] = False
    st.caption("Import inputs are available when Case 4 is selected. Duties/taxes are a blank editable assumption, not a country rate.")

saved = save_values(case_name, updates)
ui.section_title("Saved assumptions and sources")
source_rows = []
for name, value in saved.items():
    if name == "financing_template":
        source = "Selected illustrative template"
    elif name.startswith("import_"):
        source = "Editable import assumption; verify before use"
    elif name.startswith("stress_"):
        source = "Editable hypothetical stress input"
    else:
        source = "Selected case defaults or user-edited value"
    source_rows.append({"Assumption": name.replace("_", " ").title(), "Value": value, "Source": source})
source_frame = pd.DataFrame(source_rows)
source_frame["Value"] = source_frame["Value"].astype(str)
st.dataframe(source_frame, width="stretch", hide_index=True)
st.caption("Assumptions are saved in this browser session per synthetic case. Reset restores that case's generated defaults.")

ui.footer()
