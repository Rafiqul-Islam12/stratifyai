"""Financing comparison page backed by transparent illustrative calculations."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from app import charts
from app import components as ui
from core.analysis import analyze
from core.financing import TEMPLATES, FinancingTerms, calculate_financing
from core.forecast import forecast
from core.lab import run_lab
from core.loaders import load_case
from core.readiness import DEFAULT_WEIGHTS, assess_readiness
from core.readiness_pack import build_readiness_pack, verify_readiness_pack
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


@st.cache_data(show_spinner=False)
def _cached_lab(case):
    return run_lab(case)


ui.load_styles()
if ui.no_data_state("Financing", "Compare illustrative funding costs and repayment capacity."):
    st.stop()
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
    st.metric("Forecast funding gap", _money(gap),
              help="Reserve shortfall plus the configured buffer from the deterministic cash forecast.")

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

analysis = analyze(case_data)
lab_result = _cached_lab(case_data)
with st.expander("Adjust readiness indicator weights", expanded=False):
    weight_cols = st.columns(5)
    readiness_weights = {
        name: float(col.slider(f"{name.title()} weight", 0, 100, int(weight), key=f"readiness-weight-{case_name}-{name}"))
        for col, (name, weight) in zip(weight_cols, DEFAULT_WEIGHTS.items())
    }
readiness = assess_readiness(case_data, analysis, projection, capacity_ratio=result.capacity_ratio,
                             weights=readiness_weights)
ui.section_title("Financing readiness indicator")
st.caption("Readiness indicator, not a loan approval prediction. It is not a lender decision or real offer.")
if readiness.score is None:
    st.metric("Readiness indicator", "Not available",
              help="Evidence-weighted business data indicator; it is not a loan approval prediction.")
else:
    st.metric("Readiness indicator", f"{readiness.score:.1f} / 100",
              help="Evidence-weighted business data indicator; it is not a loan approval prediction.")
st.dataframe(pd.DataFrame([{
    "Component": item.name.title(), "Weight (%)": item.weight,
    "Score (0-100)": round(item.score, 1) if item.score is not None else "Not available",
    "Reason": item.reason,
} for item in readiness.components]), width="stretch", hide_index=True)
st.markdown("**Reasons and missing information**")
for note in readiness.reasons:
    st.markdown(f"- {note}")
for note in readiness.missing_information:
    st.markdown(f"- Missing: {note}")

ui.section_title("Readiness Pack")
st.caption("Integrity check only. Not a lender submission.")
expiry = st.date_input("Pack expiry date", value=date.today() + pd.Timedelta(days=30),
                       min_value=date.today(), key=f"readiness-expiry-{case_name}")
consent = st.checkbox("I consent to generate this local readiness pack", key=f"readiness-consent-{case_name}")
if st.button("Generate readiness pack", key=f"readiness-generate-{case_name}"):
    plan = lab_result.plans[lab_result.best_plan_id]
    assumptions = case_data.assumptions.model_dump()
    assumptions.update({"financing template": template, "annual rate (%)": annual_rate,
                       "fee / charge (%)": fee, "tenor (months)": int(tenor),
                       "reserve (BDT)": projection.reserve})
    try:
        pack = build_readiness_pack(case_data, analysis, projection, readiness,
            chosen_plan=f"{lab_result.best_plan_id} (remaining gap {_money(plan.remaining_gap)})",
            assumptions=assumptions, expires_on=expiry, consent=consent)
        st.session_state["readiness_pack_content"] = pack.content
        st.session_state["readiness_pack_hash"] = pack.content_hash
    except ValueError as exc:
        st.error(str(exc))
if st.session_state.get("readiness_pack_content"):
    pack_content = st.session_state["readiness_pack_content"]
    st.download_button("Download Markdown pack", data=pack_content,
        file_name=f"{case_name}-readiness-pack.md", mime="text/markdown", key=f"readiness-download-{case_name}")
    st.caption(f"SHA-256: {st.session_state['readiness_pack_hash']}")

with st.expander("Verify a readiness pack"):
    uploaded_pack = st.file_uploader("Upload Markdown or text pack", type=("md", "txt"), key=f"verify-upload-{case_name}")
    pasted_pack = st.text_area("Or paste pack content", key=f"verify-paste-{case_name}")
    if st.button("Verify pack hash", key=f"verify-pack-{case_name}"):
        candidate = uploaded_pack.getvalue().decode("utf-8", errors="replace") if uploaded_pack else pasted_pack
        verified, message = verify_readiness_pack(candidate)
        st.success(message) if verified else st.error(message)
    st.caption("Integrity check only. Not a lender submission.")
ui.footer()
