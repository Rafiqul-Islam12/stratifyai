"""Computed business overview using the existing deterministic engines."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app import charts
from app import components as ui
from core.analysis import analyze
from core.forecast import ForecastResult, forecast
from core.lab import LabResult, run_lab
from core.loaders import load_case
from core.montecarlo import MonteCarloResult, simulate
from core.readiness import assess_readiness
from data.generate_synthetic import CASES
from services.agent_actions import list_drafts
from services.audit import get_audit_events
from services.auth import current_user
from services.permissions import can_user

CASE_LABELS = {
    "stable_healthy": "Stable and healthy", "delayed_customer_payments": "Delayed customer payments",
    "high_expense_shortage": "High expense, shortage", "import_financing": "Import financing",
    "sales_drop_cost_rise": "Sales drop, cost rise",
}


@st.cache_data(show_spinner=False)
def _overview_results(case_name: str) -> tuple[ForecastResult, MonteCarloResult, LabResult]:
    case = load_case(case_name)
    projection = forecast(case)
    uncertainty = simulate(case, projection=projection)
    lab = run_lab(case)
    return projection, uncertainty, lab


def _money(value: float | None) -> str:
    return f"BDT {value:,.0f}" if value is not None else "Not available"


ui.load_styles()
user = current_user()
if user is None:
    st.error("Sign in through the StratifyAI app to view the business overview.")
    st.stop()

active = st.session_state.get("active_synthetic_case")
selected_case = st.selectbox("Synthetic demo case", options=CASES,
    index=CASES.index(active) if active in CASES else 0,
    format_func=lambda value: CASE_LABELS[value], key="overview-case-select")
with st.container():
    ui.page_header("Overview", "Business health, cash forecast and the recommended plan in one view.",
        business=CASE_LABELS[selected_case], scenario="Forecast baseline")
    source_col, load_col = st.columns([3, 1])
    with source_col:
        ui.badge("Synthetic data", "warning")
        st.caption("The selected case is deterministic demonstration data; financing terms are illustrative.")
    with load_col:
        if st.button("Load demo business", type="primary", key="overview-load-demo"):
            try:
                case = load_case(selected_case)
                st.session_state["active_synthetic_case"] = selected_case
                st.session_state["synthetic_case_data"] = case
                st.rerun()
            except (OSError, ValueError, KeyError):
                st.error("The selected synthetic case could not be loaded. Choose another case or retry.")

case_name = st.session_state.get("active_synthetic_case")
if case_name not in CASES:
    ui.empty_state("No data loaded", "Choose a synthetic demo case above, then load it to see computed cash, plans and readiness.",
                   "Load demo business", disabled=True)
    ui.footer()
    st.stop()

try:
    case = load_case(case_name)
    projection, uncertainty, lab = _overview_results(case_name)
    analysis = analyze(case)
    readiness = assess_readiness(case, analysis, projection,
        capacity_ratio=lab.plans["Option B"].capacity_ratio)
except (OSError, ValueError, KeyError, RuntimeError):
    st.error("The selected synthetic data could not be summarized. Reload the demo case or choose another one.")
    ui.empty_state("Overview unavailable", "The case results could not be computed from the validated synthetic records.",
                   "Load demo business", disabled=True)
    ui.footer()
    st.stop()

if st.session_state.get("active_synthetic_case") != case_name:
    st.session_state["active_synthetic_case"] = case_name
st.session_state["synthetic_case_data"] = case
ui.page_header("Overview", "Business health, cash forecast and the recommended plan in one view.",
    business=case.profile.business_name, scenario=CASE_LABELS[case_name])
st.caption("Synthetic data · BDT · forecast and readiness are computed from this case's validated records.")

if projection.shortage_week is None:
    ui.alert_banner("info", "No projected reserve breach",
        f"The deterministic forecast stays above the BDT {projection.reserve:,.0f} reserve. "
        f"Simulated chance of any reserve breach: {uncertainty.probability_any_reserve_breach:.1%}.")
else:
    ui.alert_banner("critical" if projection.severity == "critical" else "warning",
        "Projected reserve breach",
        f"First breach: week {projection.shortage_week}; modelled funding gap: {_money(projection.funding_gap)}. "
        f"Simulated chance of any reserve breach: {uncertainty.probability_any_reserve_breach:.1%}.")

runway = analysis.runway_weeks.value
shortage_delta = (f"week {projection.minimum_balance_week}" if projection.shortage_week is not None else "no breach projected")
ui.kpi_row([
    ("Current cash", _money(projection.opening_cash), "Latest recorded transaction balance; ACTUAL."),
    ("Minimum projected balance", _money(projection.minimum_balance),
     "Lowest deterministic FORECAST closing balance and week in the selected horizon."),
    ("Funding gap", _money(projection.funding_gap), "Forecast reserve shortfall plus the configured funding buffer."),
    ("Runway", f"{runway:.1f} weeks" if runway is not None else "Not available",
     analysis.runway_weeks.reason or "Latest recorded cash divided by recent positive weekly burn."),
    ("Overdue receivables", _money(analysis.receivables_overdue), "Open invoice balances past due at the recorded-data snapshot."),
    ("DSO", f"{analysis.dso_days.value:.1f} days" if analysis.dso_days.value is not None else "Not available",
     analysis.dso_days.reason or "Computed days sales outstanding from recorded credit sales and open invoices."),
], deltas={"Minimum projected balance": shortage_delta})

ui.section_title("Cash position")
hero = charts.base_layout(title="Actual and forecast cash balance", x_title="Week starting", y_title="BDT", height=420)
actual_x = [item.week_start.isoformat() for item in projection.actual_weeks]
forecast_x = [item.week_start.isoformat() for item in projection.forecast_weeks]
charts.line(hero, actual_x, [item.closing_balance for item in projection.actual_weeks],
    layer="ACTUAL", name="Actual closing balance")
charts.band(hero, forecast_x, uncertainty.p10, uncertainty.p90)
charts.line(hero, forecast_x, [item.closing_balance for item in projection.forecast_weeks],
    layer="FORECAST", name="Forecast closing balance")
active_scenario = st.session_state.get("global-scenario-selector", "Forecast baseline")
if active_scenario in lab.plans and active_scenario != "Option 0":
    scenario_plan = lab.plans[active_scenario]
    scenario_points = scenario_plan.balance_series_after
    charts.line(hero, [point.week_start for point in scenario_points],
        [point.closing_balance for point in scenario_points], layer="HYPOTHETICAL",
        name=f"{active_scenario} · HYPOTHETICAL")
charts.reserve(hero, actual_x + forecast_x, projection.reserve)
if projection.shortage_week is not None:
    marker_x = forecast_x[projection.shortage_week - 1]
    charts.shortage(hero, marker_x, forecast_x[-1])
    charts.shortage_marker(hero, marker_x, projection.forecast_weeks[projection.shortage_week - 1].closing_balance)
st.plotly_chart(hero, width="stretch")
ui.layer_legend()
if active_scenario in lab.plans and active_scenario != "Option 0":
    st.caption(f"The {active_scenario} line is a Decision Lab scenario and remains HYPOTHETICAL.")

ui.section_title("Recommended plan")
best = lab.plans[lab.best_plan_id]
plan_rows = [
    ("Remaining gap", _money(best.remaining_gap)),
    ("Modelled financing cost", _money(best.financing_cost)),
    ("Repayment capacity", f"{best.capacity_ratio:.2f}x" if best.capacity_ratio is not None else "Not available"),
    ("Scenario layer", ", ".join(best.layer_tags)),
]
plan_col, readiness_col = st.columns([3, 2], gap="large")
ui.plan_card(plan_col, best.plan_id, plan_rows, recommended=True)
with plan_col:
    st.caption(best.pros[0] if best.pros else lab.best_plan_reason)
    if st.button("Open Decision Lab", type="primary", key="overview-open-lab"):
        st.switch_page("pages/lab.py")
with readiness_col:
    ui.kpi_card(readiness_col, "Financing readiness indicator",
        f"{readiness.score:.1f} / 100" if readiness.score is not None else "Not available",
        tooltip="Evidence-weighted indicator; it is not a loan approval prediction.")
    with readiness_col:
        st.caption(readiness.label)
        if readiness.missing_information:
            st.caption(f"Missing information: {len(readiness.missing_information)} item(s). See Financing for details.")

ui.section_title("Receivables aging")
aging_fig = charts.base_layout(title="Overdue open receivables by age", x_title="Days past due", y_title="BDT", height=320)
aging_fig.add_bar(x=list(analysis.aging), y=list(analysis.aging.values()), marker_color=charts.PRIMARY,
                  hovertemplate="%{x}<br>BDT %{y:,.0f}<extra></extra>")
aging_fig.update_layout(showlegend=False)
st.plotly_chart(aging_fig, width="stretch")
st.caption("Aging uses outstanding invoice balances and the latest transaction date. The 90+ bucket means more than 90 days.")

approval_col, audit_col = st.columns(2, gap="large")
with approval_col:
    ui.section_title("Pending approvals")
    if user.role in {"owner", "finance_ops"}:
        try:
            pending = list_drafts(user, status="pending_approval")
            if pending:
                st.metric("Waiting for owner review", len(pending), help="Submitted drafts; approval remains owner-only.")
                st.write(" · ".join(f"{draft.action_type.replace('_', ' ').title()} ({draft.draft_id[:8]})" for draft in pending[:5]))
            else:
                st.caption("No pending approvals.")
        except Exception:  # noqa: BLE001 - overview remains available if local draft storage is unavailable
            st.info("Pending approval data is unavailable. Check the Approvals page.")
    else:
        st.caption("Pending draft details are not available for this role.")

with audit_col:
    ui.section_title("Latest audit events")
    if can_user(user, "audit.view"):
        try:
            events = get_audit_events(user, limit=5)
            if events:
                st.dataframe(pd.DataFrame([{"Time": row["ts"], "Action": row["action"],
                    "Result": row["entity"]} for row in events]), width="stretch", hide_index=True)
            else:
                st.caption("No audit events yet.")
        except Exception:  # noqa: BLE001 - avoid showing local audit or database details
            st.info("Audit events are unavailable. Check the Security page.")
    else:
        st.caption("Audit events are restricted to owner and auditor roles.")

ui.footer()
