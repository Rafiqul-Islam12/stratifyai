"""Financing comparison page backed by transparent illustrative calculations."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app import charts
from app import components as ui
from core.financing import TEMPLATES, FinancingTerms, calculate_financing
from core.forecast import forecast
from core.loaders import load_case
from data.generate_synthetic import CASES

CASE_LABELS = {
    "stable_healthy": "Stable and healthy", "delayed_customer_payments": "Delayed customer payments",
    "high_expense_shortage": "High expense, shortage", "import_financing": "Import financing",
    "sales_drop_cost_rise": "Sales drop, cost rise",
}
DEFAULTS = {
    "Term loan": (14.0, 1.0, 6, 80.0), "Invoice financing": (0.0, 2.0, 1, 80.0),
    "Supplier credit": (0.0, 1.5, 1, 80.0), "Credit line": (16.0, 0.5, 6, 80.0),
}


def _money(amount: float) -> str:
    return f"BDT {amount:,.0f}"


ui.load_styles()
initial_case = st.session_state.get("active_synthetic_case", "high_expense_shortage")
case_index = CASES.index(initial_case) if initial_case in CASES else CASES.index("high_expense_shortage")
case_name = st.selectbox("Synthetic demo case", CASES, index=case_index,
                         format_func=lambda value: CASE_LABELS[value], key="financing-case-select")
case_data = load_case(case_name)
st.session_state["active_synthetic_case"] = case_name
st.session_state["synthetic_case_data"] = case_data
projection = forecast(case_data)

ui.page_header("Financing", "Compare illustrative funding costs and repayment capacity.",
               business=case_data.profile.business_name, scenario=CASE_LABELS[case_name])
ui.alert_banner("warning", "Illustrative terms, not real lender offers",
                "These estimates are examples only. Confirm every term with the relevant counterparty.")
st.caption("Synthetic data · BDT · funding need is based on the deterministic cash forecast.")

gap = max(0.0, projection.funding_gap)
template = st.selectbox("Financing template", TEMPLATES, key="financing-template")
default_rate, default_fee, default_months, default_advance = DEFAULTS[template]
left, right = st.columns(2)
with left:
    tenor = st.number_input("Tenor (months)", min_value=1, max_value=120, value=default_months,
                            step=1, key=f"financing-tenor-{template}")
    if template in ("Term loan", "Credit line"):
        annual_rate = st.number_input("Annual interest rate (%)", min_value=0.0, max_value=100.0,
                                      value=default_rate, step=0.5, key=f"financing-rate-{template}")
    else:
        annual_rate = 0.0
    fee_label = {"Invoice financing": "Fee per 30 days (%)", "Supplier credit": "Cost of invoice value (%)"}.get(template, "Upfront fee (%)")
    fee = st.number_input(fee_label, min_value=0.0, max_value=100.0, value=default_fee,
                          step=0.25, key=f"financing-fee-{template}")
with right:
    advance = st.number_input("Advance rate (%)", min_value=1.0, max_value=100.0,
                              value=default_advance, step=1.0, key=f"financing-advance-{template}") if template == "Invoice financing" else default_advance
    st.metric("Forecast funding gap", _money(gap))

terms = FinancingTerms(float(annual_rate), float(fee), int(tenor), float(advance))
result = calculate_financing(template, gap, terms, projection)
st.session_state["financing_result"] = result
ratio_display = f"{result.capacity_ratio:.2f}x" if result.capacity_ratio is not None else "—"
ui.kpi_row([
    ("Facility amount", _money(result.amount), "Rounded up to BDT 1,000; invoice financing is grossed up for its advance rate."),
    ("Total interest", _money(result.interest), "Modelled interest or periodic financing charge."),
    ("Fees", _money(result.fees), "Modelled explicit fees."),
    ("Total cost", _money(result.total_cost), "Interest and fees over the modelled term."),
])
ui.kpi_row([
    ("Total repayment", _money(result.total_repayment), "Facility principal plus modelled cost."),
    ("Repayment capacity", ratio_display, "Average forecast weekly net operating cash flow × 52/12 ÷ monthly debt service."),
    ("Capacity pressure", result.pressure_label, "Rules of thumb: ≥1.25 comfortable; 1.0–1.25 tight; below 1.0 stressed."),
    ("Tenor", f"{tenor} months", "Editable illustrative repayment period."),
])

ui.section_title("Repayment schedule")
if result.schedule:
    st.dataframe(pd.DataFrame([{
        "Month": row.month, "Opening balance (BDT)": round(row.opening_balance, 2),
        "Payment (BDT)": round(row.payment, 2), "Principal (BDT)": round(row.principal, 2),
        "Interest / charge (BDT)": round(row.interest, 2), "Closing balance (BDT)": round(row.closing_balance, 2),
    } for row in result.schedule]), width="stretch", hide_index=True)
else:
    ui.empty_state("No repayment schedule", "The funding gap is zero, so this template sizes no facility.",
                   "Load demo business", disabled=True)

ui.section_title("Cost breakdown")
fig = charts.base_layout(title="Illustrative financing cost", y_title="BDT", height=320)
fig.add_bar(x=["Interest / charges", "Fees"], y=[result.interest, result.fees],
            marker_color=[charts.PRIMARY, charts.BORDER], name="Cost")
fig.update_layout(showlegend=False)
st.plotly_chart(fig, width="stretch")

ui.section_title("Risks and information gaps")
for note in result.risk_notes or ("No template-specific risk flag was triggered by the current inputs.",):
    st.markdown(f"- {note}")
st.markdown("**Information to confirm**")
for item in result.missing_information:
    st.markdown(f"- {item}")
st.caption("Capacity pressure labels are simple modelling thresholds, not lender rules. Invoice financing charges use the selected fee per 30 days; supplier credit cost is a one-time percentage. Credit line fees are applied to the drawn amount because a separate undrawn limit was not modelled.")
ui.footer()
