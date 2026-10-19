"""Interactive comparison of deterministic baseline, levers, stress and financing."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app import charts
from app import components as ui
from app.assumptions_store import get_values, save_values, to_lab_assumptions, to_stress_inputs
from core.forecast import forecast
from core.import_scenario import ImportInputs, build_import_scenario
from core.lab import run_lab
from core.loaders import load_case
from core.montecarlo import simulate
from core.stress import apply_stress
from services.actions import record_scenario_change
from services.actions import run_lab as run_authorized_lab
from services.agent_actions import confirmed_plans, create_draft, submit_draft
from services.auth import current_user
from services.permissions import can_user

CASE_LABELS = {
    "stable_healthy": "Stable and healthy", "delayed_customer_payments": "Delayed customer payments",
    "high_expense_shortage": "High expense, shortage", "import_financing": "Import financing",
    "sales_drop_cost_rise": "Sales drop, cost rise",
}
PLAN_ORDER = ("Option 0", "Option A", "Option B", "Option C")


def _money(value: float) -> str:
    return f"BDT {value:,.0f}"


def _shortage(value: int | None) -> str:
    return f"Week {value}" if value is not None else "None"


@st.cache_data(show_spinner=False)
def _cached_lab(case, assumptions):
    return run_lab(case, assumptions)


@st.cache_data(show_spinner=False)
def _cached_plan_mc(case, projection, inflow_delta, outflow_delta, adjustments, reserve, cv, delay_sd):
    return simulate(case, projection=projection, inflow_adjustments=inflow_delta, outflow_adjustments=outflow_delta,
                    balance_adjustments=adjustments, reserve=reserve,
                    sales_variability_cv=cv, customer_delay_sd_days=delay_sd)


def _render_controls(case_name: str, case, values: dict, stress_tab) -> dict:
    updates = dict(values)
    with st.container():
        st.caption("Controls save to the session assumption store and recalculate this comparison immediately.")
        ui.section_title("Reserve and horizon")
        cols = st.columns(4)
        updates["reserve_mode"] = cols[0].selectbox("Reserve method", ("Reserve weeks", "Fixed BDT"),
            index=("Reserve weeks", "Fixed BDT").index(values["reserve_mode"]), key=f"lab::{case_name}::reserve_mode")
        if updates["reserve_mode"] == "Fixed BDT":
            updates["reserve_bdt"] = cols[1].number_input("Minimum reserve (BDT)", min_value=0, max_value=100_000_000,
                value=int(values["reserve_bdt"]), step=10_000, key=f"lab::{case_name}::reserve_bdt")
        else:
            updates["reserve_weeks"] = cols[1].slider("Reserve basis (weeks)", 0.0, 13.0,
                float(values["reserve_weeks"]), step=0.5, key=f"lab::{case_name}::reserve_weeks")
            updates["reserve_bdt"] = round(forecast(case, reserve_weeks=float(updates["reserve_weeks"]),
                horizon_weeks=int(values["horizon_weeks"])).reserve)
            cols[1].caption(f"Derived reserve: BDT {updates['reserve_bdt']:,.0f}")
        updates["horizon_weeks"] = cols[2].slider("Forecast horizon (weeks)", 8, 13, int(values["horizon_weeks"]),
            key=f"lab::{case_name}::horizon_weeks")
        updates["funding_buffer_pct"] = cols[3].slider("Funding gap buffer (%)", 0.0, 50.0,
            float(values["funding_buffer_pct"]), step=1.0, key=f"lab::{case_name}::funding_buffer_pct")
        cols = st.columns(2)
        updates["sales_variability_cv"] = cols[0].slider("Sales variability (CV)", 0.0, 1.0,
            float(values["sales_variability_cv"]), step=0.05, key=f"lab::{case_name}::sales_variability_cv",
            help="Coefficient of variation for weekly cash receipts; 0 removes sales amount volatility.")
        updates["customer_delay_sd_days"] = cols[1].slider("Customer delay SD (days)", 0, 90,
            int(values["customer_delay_sd_days"]), key=f"lab::{case_name}::customer_delay_sd_days")

        ui.section_title("Option A levers")
        cols = st.columns(4)
        updates["collection_pct"] = cols[0].slider("L1 collections (%)", 0, 100, int(values["collection_pct"]), key=f"lab::{case_name}::collection_pct")
        updates["collection_weeks"] = cols[1].slider("L1 collection window (weeks)", 1, 13, min(13, int(values["collection_weeks"])), key=f"lab::{case_name}::collection_weeks")
        updates["collection_haircut_pct"] = cols[2].slider("L1 haircut (%)", 0, 100, int(values["collection_haircut_pct"]), key=f"lab::{case_name}::collection_haircut_pct")
        updates["deferral_weeks"] = cols[3].slider("L2 defer (weeks)", 1, 8, min(8, int(values["deferral_weeks"])), key=f"lab::{case_name}::deferral_weeks")
        cols = st.columns(3)
        updates["late_fee_pct"] = cols[0].slider("L2 late fee (%)", 0.0, 25.0, min(25.0, float(values["late_fee_pct"])), step=0.25, key=f"lab::{case_name}::late_fee_pct")
        updates["discretionary_reduction_pct"] = cols[1].slider("L3 expense reduction (%)", 0, 80, min(80, int(values["discretionary_reduction_pct"])), key=f"lab::{case_name}::discretionary_reduction_pct")
        updates["discretionary_start_week"] = cols[2].slider("L3 starts in week", 1, 13, min(13, int(values["discretionary_start_week"])), key=f"lab::{case_name}::discretionary_start_week")

        ui.section_title("Financing terms")
        templates = ("Term loan", "Invoice financing", "Supplier credit", "Credit line")
        cols = st.columns(5)
        updates["financing_template"] = cols[0].selectbox("Template", templates, index=templates.index(values["financing_template"]), key=f"lab::{case_name}::financing_template")
        updates["annual_rate_pct"] = cols[1].number_input("Annual rate (%)", min_value=0.0, max_value=100.0, value=float(values["annual_rate_pct"]), step=0.5, key=f"lab::{case_name}::annual_rate_pct")
        updates["fee_pct"] = cols[2].number_input("Fee / charge (%)", min_value=0.0, max_value=100.0, value=float(values["fee_pct"]), step=0.25, key=f"lab::{case_name}::fee_pct")
        updates["tenor_months"] = cols[3].number_input("Tenor (months)", min_value=1, max_value=120, value=int(values["tenor_months"]), key=f"lab::{case_name}::tenor_months")
        updates["advance_pct"] = cols[4].number_input("Invoice advance (%)", min_value=1.0, max_value=100.0, value=float(values["advance_pct"]), step=1.0, key=f"lab::{case_name}::advance_pct")

        with stress_tab:
            ui.section_title("Stress inputs")
            cols = st.columns(4)
            updates["stress_sales_drop_pct"] = cols[0].slider("Sales decrease (%)", 0.0, 50.0, min(50.0, float(values["stress_sales_drop_pct"])), step=1.0, key=f"lab::{case_name}::stress_sales_drop_pct")
            updates["stress_cost_increase_pct"] = cols[1].slider("Costs increase (%)", 0.0, 100.0, min(100.0, float(values["stress_cost_increase_pct"])), step=1.0, key=f"lab::{case_name}::stress_cost_increase_pct")
            updates["stress_delay_days"] = cols[2].slider("Customer delay +days", 0, 180, min(180, int(values["stress_delay_days"])), key=f"lab::{case_name}::stress_delay_days")
            updates["stress_fx_shock_pct"] = cols[3].slider("FX shock (%)", -50.0, 100.0, min(100.0, max(-50.0, float(values["stress_fx_shock_pct"]))), step=1.0, key=f"lab::{case_name}::stress_fx_shock_pct")

        if case.profile.import_scenario:
            ui.section_title("Case 4 import scenario")
            updates["include_import_scenario"] = st.checkbox("Include hypothetical import shipment", bool(values["include_import_scenario"]), key=f"lab::{case_name}::include_import_scenario")
            cols = st.columns(4)
            updates["import_product_cost_foreign"] = cols[0].number_input("Product cost (foreign units)", min_value=0.0, max_value=1_000_000_000.0, value=float(values["import_product_cost_foreign"]), step=100.0, key=f"lab::{case_name}::import_product_cost_foreign")
            updates["import_deposit_pct"] = cols[1].slider("Deposit (%)", 0.0, 100.0, float(values["import_deposit_pct"]), key=f"lab::{case_name}::import_deposit_pct")
            updates["import_shipping_cost_foreign"] = cols[2].number_input("Shipping (foreign units)", min_value=0.0, max_value=1_000_000_000.0, value=float(values["import_shipping_cost_foreign"]), step=100.0, key=f"lab::{case_name}::import_shipping_cost_foreign")
            updates["import_duties_taxes_pct"] = cols[3].slider("Duties / taxes assumption (%)", 0.0, 100.0, float(values["import_duties_taxes_pct"]), key=f"lab::{case_name}::import_duties_taxes_pct")
            cols = st.columns(4)
            updates["import_fx_rate"] = cols[0].number_input("FX rate (BDT per unit)", min_value=0.000001, max_value=100_000.0, value=float(values["import_fx_rate"]), step=1.0, key=f"lab::{case_name}::import_fx_rate")
            updates["import_fx_shock_pct"] = cols[1].slider("Import FX shock (%)", -100.0, 200.0, float(values["import_fx_shock_pct"]), key=f"lab::{case_name}::import_fx_shock_pct")
            updates["import_lead_time_weeks"] = cols[2].number_input("Lead time (weeks)", min_value=1, max_value=52, value=int(values["import_lead_time_weeks"]), key=f"lab::{case_name}::import_lead_time_weeks")
            updates["import_sales_ramp_weeks"] = cols[3].number_input("Sales ramp (weeks)", min_value=1, max_value=52, value=int(values["import_sales_ramp_weeks"]), key=f"lab::{case_name}::import_sales_ramp_weeks")
            updates["import_collection_delay_days"] = st.number_input("New sales collection delay (days)", min_value=0, max_value=365, value=int(values["import_collection_delay_days"]), key=f"lab::{case_name}::import_collection_delay_days")
    return save_values(case_name, updates)


ui.load_styles()
user = current_user()
if user is not None and not can_user(user, "lab.run"):
    ui.locked_card("Decision Lab is not available for this role", "Running and changing scenarios needs a role that can draft hypothetical changes.", "owner, finance_ops")
    ui.footer()
    st.stop()
if ui.no_data_state("Liquidity Decision Lab", "Compare baseline cash, levers and financing."):
    st.stop()
active = st.session_state.get("active_synthetic_case", "high_expense_shortage")
case_name = ui.active_case("lab-case-select", default_case="high_expense_shortage")
case = load_case(case_name)
st.session_state["active_synthetic_case"] = case_name
st.session_state["synthetic_case_data"] = case
ui.page_header("Liquidity Decision Lab", "Compare baseline cash, operational levers, stress and illustrative financing.",
               business=case.profile.business_name, scenario=CASE_LABELS[case_name])
values = get_values(case_name, case)
summary = st.container()
tab_compare, tab_levers, tab_stress, tab_details, tab_scenarios = st.tabs(
    ["Compare plans", "Levers and assumptions", "Stress tests", "Plan details", "Scenarios and proposal"])
with tab_levers:
    values = _render_controls(case_name, case, values, tab_stress)
snapshot_key = f"lab_authorized_snapshot::{case_name}"
previous_values = st.session_state.get(snapshot_key, {})
changed_fields = sorted(key for key, value in values.items() if previous_values.get(key) != value)
if user and changed_fields:
    audit_reference = record_scenario_change(user, case_name, changed_fields)
    st.session_state.setdefault("lab_audit_references", {}).setdefault(case_name, []).append(audit_reference)
st.session_state[snapshot_key] = dict(values)

stress = apply_stress(case, to_stress_inputs(values))
scenario_case = stress.case
import_result = None
if case.profile.import_scenario and values["include_import_scenario"]:
    import_inputs = ImportInputs(
        float(values["import_product_cost_foreign"]), float(values["import_deposit_pct"]),
        float(values["import_shipping_cost_foreign"]), float(values["import_duties_taxes_pct"]),
        float(values["import_fx_rate"]), float(values["import_fx_shock_pct"]),
        int(values["import_lead_time_weeks"]), int(values["import_sales_ramp_weeks"]),
        int(values["import_collection_delay_days"]),
    )
    import_result = build_import_scenario(scenario_case, import_inputs)
    scenario_case = import_result.scenario_case
lab_assumptions = to_lab_assumptions(values)
lab_result = run_authorized_lab(user, scenario_case, lab_assumptions) if user else _cached_lab(scenario_case, lab_assumptions)
confirmed = confirmed_plans(user, case_name) if user else []
st.session_state["lab_result"] = lab_result
st.session_state["lab_case_name"] = case_name
st.session_state["lab_scenario_case"] = scenario_case
st.session_state["lab_stress_result"] = stress
st.session_state["lab_import_result"] = import_result

baseline = lab_result.plans["Option 0"]
selected = lab_result.plans[lab_result.best_plan_id]

def _decision_report() -> str:
    """Build a downloadable snapshot from the exact case and Lab result on screen."""
    from datetime import UTC, datetime

    lines = [
        "# Liquidity Decision Lab report", "", f"Generated: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"Business: {case.profile.business_name}", f"Case: {case_name}", f"Currency: {case.profile.currency}",
        "Data label: Synthetic data", "", "## Assumptions and sources", "",
        f"- Minimum reserve: BDT {lab_result.reserve:,.2f} (from the forecast and current Lab assumptions).",
        f"- Forecast horizon: {len(baseline.balance_series_after)} weeks.",
        f"- Financing template: {values['financing_template']} (illustrative and editable).",
        f"- Scenario levers: collection {values['collection_pct']}%; deferral {values['deferral_weeks']} weeks; discretionary reduction {values['discretionary_reduction_pct']}%.",
        "- Detailed plan assumptions and source descriptions are listed in the comparison below.", "",
        "## Recommendation under the deterministic rule", "",
        f"- Selected: {lab_result.best_plan_id}.", f"- Reason: {lab_result.best_plan_reason}",
        f"- Borrowing necessary in this model: {lab_result.borrowing_necessary}. {lab_result.borrowing_reason}", "",
        "## Plan comparison", "", "| Plan | Layer | Minimum balance (BDT) | Reserve gap (BDT) | Financing (BDT) | Cost (BDT) | Repayment capacity | Reserve breach probability |", "|---|---|---:|---:|---:|---:|---|---:|"
    ]
    for plan_name, plan in lab_result.plans.items():
        minimum = min((point.closing_balance for point in plan.balance_series_after), default=0.0)
        breach = "unavailable" if plan.breach_probability is None else f"{plan.breach_probability:.2%}"
        capacity = "unavailable" if plan.capacity_ratio is None else f"{plan.capacity_ratio:.2f} ({plan.capacity_label})"
        lines.append(f"| {plan_name} | {', '.join(plan.layer_tags)} | {minimum:,.2f} | {plan.remaining_gap:,.2f} | {plan.financing_amount:,.2f} | {plan.financing_cost:,.2f} | {capacity} | {breach} |")
    lines.extend(["", "## Weekly balance table", "", "| Week | Date | Option 0 forecast (BDT) | Selected plan (BDT) | Layer |", "|---:|---|---:|---:|---|"])
    best = lab_result.plans[lab_result.best_plan_id]
    for base_point, best_point in zip(baseline.balance_series_after, best.balance_series_after):
        lines.append(f"| {base_point.week} | {base_point.week_start} | {base_point.closing_balance:,.2f} | {best_point.closing_balance:,.2f} | {best_point.layer} |")
    refs = st.session_state.get("lab_audit_references", {}).get(case_name, [])
    lines.extend(["", "## Audit references", "", ", ".join(f"scenario.changed event {event_id}" for event_id in refs[-20:]) if refs else "No scenario-change audit event ID was recorded for these settings in this session.",
                  "", "## Layers and limitations", "",
                  "ACTUAL records, FORECAST outputs, HYPOTHETICAL plan changes and CONFIRMED owner-approved assumptions remain separate. Plan changes are hypothetical until owner approval. This report is based on synthetic case data; financing terms are illustrative. It is not a lender decision or an approval, and it does not assume customer payment, supplier agreement or real-world execution."])
    return "\n".join(lines) + "\n"

decision_report = _decision_report()
st.session_state["lab_decision_report"] = decision_report
with summary:
    st.download_button("Download decision report (Markdown)", data=decision_report,
                       file_name=f"stratifyai-decision-report-{case_name}.md", mime="text/markdown",
                       key=f"lab-decision-report-{case_name}")
    ui.alert_banner(
        "success" if selected.is_feasible else "warning",
        f"Recommended plan: {lab_result.best_plan_id}" if selected.is_feasible else f"No plan fully closes the gap · smallest gap: {lab_result.best_plan_id}",
        lab_result.best_plan_reason,
    )
    first_shortage = _shortage(baseline.shortage_week)
    ui.kpi_row([
        ("Scenario funding gap", _money(baseline.funding_gap), "Reserve minus the lowest projected balance under the current case and stress settings, before levers or financing."),
        ("Baseline shortage", first_shortage, "First forecast week that closes below the selected reserve."),
        ("Recommended plan", lab_result.best_plan_id, lab_result.best_plan_reason),
        ("Borrowing necessary?", "Yes" if lab_result.borrowing_necessary else "No", lab_result.borrowing_reason),
    ])

with tab_compare:
    ui.section_title("Five decision questions")
    questions = list(lab_result.key_answers.values())
    cols = st.columns(5)
    for col, answer in zip(cols, questions):
        value = answer["answer"]
        if isinstance(value, float):
            shown = _money(value)
        elif isinstance(value, bool):
            shown = "Yes" if value else "No"
        elif value is None:
            shown = "None"
        else:
            shown = str(value)
        col.metric(str(answer["question"]), shown)

with summary:
    ui.section_title("Plan comparison")
    _plans = []
    for name in PLAN_ORDER:
        plan = lab_result.plans[name]
        min_balance = min(point.closing_balance for point in plan.balance_series_after)
        shortage_date = plan.balance_series_after[plan.shortage_week - 1].week_start if plan.shortage_week else "None"
        _plans.append((name, [
            ("Minimum balance", _money(min_balance)),
            ("Gap before finance", _money(plan.funding_gap)),
            ("Remaining gap", _money(plan.remaining_gap)),
            ("First shortage", _shortage(plan.shortage_week)),
            ("Reserve breach probability", f"{plan.breach_probability:.1%}" if plan.breach_probability is not None else "Unavailable"),
            ("Shortage date", str(shortage_date)),
            ("Facility", _money(plan.financing_amount)),
            ("Financing cost", _money(plan.financing_cost)),
            ("Capacity", f"{plan.capacity_ratio:.2f}x · {plan.capacity_label}" if plan.capacity_ratio is not None else plan.capacity_label),
            ("Status", "Feasible" if plan.is_feasible else "Gap remains"),
            ("Layer", ", ".join(plan.layer_tags)),
        ], name == lab_result.best_plan_id))
    ui.plan_row(_plans)

with tab_compare:
    ui.section_title("Balance by plan")
    first_plan = lab_result.plans["Option 0"].balance_series_after
    week_labels = [point.week_start for point in first_plan]
    figure = charts.base_layout(title="Projected closing balance", x_title="Week starting", y_title="BDT", height=420)
    scenario_active = any((float(values["stress_sales_drop_pct"]), float(values["stress_cost_increase_pct"]),
                           int(values["stress_delay_days"]), float(values["stress_fx_shock_pct"]))) or import_result is not None
    for name in PLAN_ORDER:
        plan = lab_result.plans[name]
        layer = "HYPOTHETICAL" if name != "Option 0" or scenario_active else "FORECAST"
        charts.line(figure, week_labels, [point.closing_balance for point in plan.balance_series_after], layer=layer, name=name)
        plan_projection = forecast(scenario_case, reserve=lab_result.reserve)
        base_inflows = tuple(week.inflow for week in plan_projection.forecast_weeks)
        base_outflows = tuple(week.outflow for week in plan_projection.forecast_weeks)
        mc = _cached_plan_mc(scenario_case, plan_projection,
            tuple(a - b for a, b in zip(plan.simulation_inflows, base_inflows)),
            tuple(a - b for a, b in zip(plan.simulation_outflows, base_outflows)), plan.simulation_adjustments,
            lab_result.reserve, float(values["sales_variability_cv"]), float(values["customer_delay_sd_days"]))
        if name == "Option 0":
            charts.band(figure, week_labels, mc.p10, mc.p90)
    for proposal in confirmed:
        snapshot = proposal.get("plan_snapshot", {})
        points = snapshot.get("balance_series_after", [])
        if points:
            charts.line(figure, [point["week_start"] for point in points],
                        [point["closing_balance"] for point in points], layer="CONFIRMED",
                        name=f"Confirmed · {proposal.get('plan_id', 'Lab plan')}")
    charts.reserve(figure, week_labels, lab_result.reserve)
    st.plotly_chart(charts.polish(figure), width="stretch")
    ui.layer_legend()

    ui.section_title("Financing cost and gap reduction")
    cost_gap = charts.base_layout(title="Financing cost vs reserve-gap reduction", x_title="Gap reduction (BDT)", y_title="Financing cost (BDT)", height=340)
    for name in PLAN_ORDER:
        plan = lab_result.plans[name]
        reduction = baseline.funding_gap - plan.remaining_gap
        cost_gap.add_scatter(x=[reduction], y=[plan.financing_cost], mode="markers+text", text=[name],
                             textposition="top center", name=name, showlegend=False)
    st.plotly_chart(charts.polish(cost_gap), width="stretch")

    ui.section_title("Option A lever breakdown")
    lever_chart = charts.base_layout(title="Reserve-gap reduction by isolated lever", x_title="Lever", y_title="Gap reduction (BDT)", height=320)
    lever_names = ("L1", "L2", "L3")
    lever_gains = [baseline.funding_gap - lab_result.plans[name].remaining_gap for name in lever_names]
    lever_chart.add_bar(x=lever_names, y=lever_gains, marker_color=charts.PRIMARY, name="Gap reduction")
    lever_chart.update_layout(showlegend=False)
    st.plotly_chart(charts.polish(lever_chart), width="stretch")

with tab_details:
    if import_result:
        with st.expander("Hypothetical import cash events and assumptions", expanded=False):
            st.caption("Product and shipping inputs are foreign currency units converted at the editable BDT rate. Duties/taxes are user-entered assumptions, not country rules.")
            st.dataframe(pd.DataFrame([{
                "Week": event.week, "Date": event.date, "Event": event.event,
                "Amount (BDT)": round(event.amount_bdt, 2), "Layer": event.layer,
            } for event in import_result.events]), width="stretch", hide_index=True)
            import_assumptions = pd.DataFrame(import_result.assumptions_with_sources)
            import_assumptions["value"] = import_assumptions["value"].astype(str)
            st.dataframe(import_assumptions, width="stretch", hide_index=True)

    ui.section_title("Plan details")
    for name in PLAN_ORDER:
        plan = lab_result.plans[name]
        with st.expander(f"{name}: assumptions, sources, risks, pros, cons and next steps", expanded=name == lab_result.best_plan_id):
            left, right = st.columns(2)
            left.markdown("**Assumptions and sources**")
            source_frame = pd.DataFrame(plan.assumptions_with_sources)
            if "value" in source_frame:
                source_frame["value"] = source_frame["value"].astype(str)
            left.dataframe(source_frame, width="stretch", hide_index=True)
            right.markdown("**Risks**")
            for note in plan.risks or ("No plan-specific risk flag was triggered.",):
                right.markdown(f"- {note}")
            right.markdown("**Pros**")
            for item in plan.pros:
                right.markdown(f"- {item}")
            right.markdown("**Cons**")
            for item in plan.cons:
                right.markdown(f"- {item}")
            right.markdown("**Next steps**")
            for item in plan.next_steps:
                right.markdown(f"- {item}")
            if plan.breach_probability_by_week:
                peak_week = max(range(len(plan.breach_probability_by_week)), key=plan.breach_probability_by_week.__getitem__)
                st.caption(f"Probability of falling below reserve in week {peak_week + 1}: "
                           f"{plan.breach_probability_by_week[peak_week]:.1%}; "
                           f"chance of any reserve breach: {plan.breach_probability:.1%}.")

    with st.expander("Stress assumptions and sources", expanded=False):
        stress_frame = pd.DataFrame(stress.assumptions)
        stress_frame["value"] = stress_frame["value"].astype(str)
        st.dataframe(stress_frame, width="stretch", hide_index=True)
        for note in stress.risk_notes:
            st.markdown(f"- {note}")

with tab_scenarios:
    ui.section_title("Save and compare scenarios")
    saved_scenarios = st.session_state.setdefault("lab_saved_scenarios", {}).setdefault(case_name, [])
    cols = st.columns([3, 1])
    scenario_name = cols[0].text_input("Scenario name", value=f"Scenario {len(saved_scenarios) + 1}", key=f"lab-save-name-{case_name}")
    if cols[1].button("Save scenario", disabled=len(saved_scenarios) >= 3, key=f"lab-save-{case_name}"):
        snapshot = {
            "name": scenario_name.strip() or f"Scenario {len(saved_scenarios) + 1}",
            "best plan": lab_result.best_plan_id,
            "funding gap (BDT)": baseline.funding_gap,
            "Option A remaining (BDT)": lab_result.plans["Option A"].remaining_gap,
            "Option B facility (BDT)": lab_result.plans["Option B"].financing_amount,
            "Option C facility (BDT)": lab_result.plans["Option C"].financing_amount,
            "Option A cost (BDT)": lab_result.plans["Option A"].financing_cost,
            "stress sales decrease (%)": values["stress_sales_drop_pct"],
            "stress cost increase (%)": values["stress_cost_increase_pct"],
            "stress delay (days)": values["stress_delay_days"],
            "FX shock (%)": values["stress_fx_shock_pct"],
            "L1 collection (%)": values["collection_pct"],
            "L2 deferral (weeks)": values["deferral_weeks"],
            "L3 reduction (%)": values["discretionary_reduction_pct"],
            "reserve mode": values["reserve_mode"],
            "reserve (BDT)": lab_result.reserve,
            "financing template": values["financing_template"],
            "annual rate (%)": values["annual_rate_pct"],
            "fee (%)": values["fee_pct"],
            "tenor (months)": values["tenor_months"],
            "import included": bool(import_result),
            "import FX rate": values["import_fx_rate"] if import_result else None,
            "import FX shock (%)": values["import_fx_shock_pct"] if import_result else None,
            "import deposit (%)": values["import_deposit_pct"] if import_result else None,
        }
        saved_scenarios.append(snapshot)
        st.rerun()
    if saved_scenarios:
        st.dataframe(pd.DataFrame(saved_scenarios), width="stretch", hide_index=True)
        st.caption(f"{len(saved_scenarios)} of 3 scenarios saved for {CASE_LABELS[case_name]}.")
    else:
        st.caption("Save up to three settings snapshots to compare them in this session.")

    ui.section_title("Submit a plan proposal")
    proposal_plan_id = st.selectbox("Plan to submit", PLAN_ORDER, index=PLAN_ORDER.index(lab_result.best_plan_id)
        if lab_result.best_plan_id in PLAN_ORDER else 0, key=f"lab-proposal-plan-{case_name}")
    if st.button("Save as proposal", disabled=user is None, key=f"lab-proposal-save-{case_name}"):
        try:
            plan_snapshot = lab_result.plans[proposal_plan_id].to_dict()
            draft = create_draft(user, "plan_proposal", {
                "case_name": case_name,
                "plan_id": proposal_plan_id,
                "plan_snapshot": plan_snapshot,
            })
            submit_draft(user, draft.draft_id)
            st.success(f"Proposal {draft.draft_id[:8]} submitted for owner review. Assumptions remain HYPOTHETICAL until approved.")
            st.rerun()
        except Exception:  # noqa: BLE001 - don't expose persistence or internal plan details
            st.error("The plan proposal could not be saved. No external action was taken.")
ui.footer()
