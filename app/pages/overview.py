"""Computed business overview using the existing deterministic engines."""
from __future__ import annotations

import streamlit as st

from app import charts, landing
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

CASE_LABELS = ui.CASE_LABELS


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

visible_pages = {path for _, path, _ in ui.PAGES if path not in ui.PAGE_ACTIONS or can_user(user, ui.PAGE_ACTIONS[path])}
ui.page_header("Overview", "Business health, cash forecast and the recommended plan in one view.")

case_name = st.session_state.get("active_synthetic_case")
if case_name not in CASES:
    _slot = st.container(key="card-overview-empty")
    with _slot:
        ui.section_title("Get started")
        st.markdown('<div class="sa-empty"><div class="sa-empty-title">No data loaded</div><div class="sa-empty-body">'
                    "Choose a labelled synthetic business to see computed cash, plans and readiness.</div></div>",
                    unsafe_allow_html=True)
        pick_col, load_col = st.columns([3, 2], vertical_alignment="bottom")
        selected_case = pick_col.selectbox("Synthetic demo case", options=CASES, format_func=lambda value: CASE_LABELS[value],
                                           key="overview-case-select")
        if load_col.button("Load demo business", type="primary", key="overview-load-demo", use_container_width=True):
            try:
                st.session_state["active_synthetic_case"] = selected_case
                st.session_state["synthetic_case_data"] = load_case(selected_case)
                st.rerun()
            except (OSError, ValueError, KeyError):
                st.session_state["active_synthetic_case"] = None
                st.error("The selected synthetic case could not be loaded. Choose another case or retry.")
    landing.how_it_works_signed_in(user, visible_pages)
    ui.footer()
    st.stop()

try:
    case = load_case(case_name)
    projection, uncertainty, lab = _overview_results(case_name)
    analysis = analyze(case)
    readiness = assess_readiness(case, analysis, projection, capacity_ratio=lab.plans["Option B"].capacity_ratio)
except (OSError, ValueError, KeyError, RuntimeError):
    st.error("The selected synthetic data could not be summarized. Reload the demo case or choose another one.")
    ui.empty_state("Overview unavailable", "The case results could not be computed from the validated synthetic records.",
                   "Load demo business", disabled=True)
    ui.footer()
    st.stop()

st.session_state["synthetic_case_data"] = case

if projection.shortage_week is None:
    ui.alert_banner("success", "No projected reserve breach",
        f"The deterministic forecast stays above the BDT {projection.reserve:,.0f} reserve. "
        f"Simulated chance of any reserve breach: {uncertainty.probability_any_reserve_breach:.1%}.")
else:
    ui.alert_banner("critical" if projection.severity == "critical" else "warning", "Projected reserve breach",
        f"First breach: week {projection.shortage_week}; modelled funding gap: {_money(projection.funding_gap)}. "
        f"Simulated chance of any reserve breach: {uncertainty.probability_any_reserve_breach:.1%}.")

runway = analysis.runway_weeks.value
recent = [week.closing_balance for week in projection.actual_weeks[-13:]]
ui.hero_card(
    "Current cash", _money(projection.opening_cash),
    lines=[f"Reserve {_money(projection.reserve)}", f"Runway {runway:.1f} weeks" if runway is not None else "Runway not available",
           f"Lowest projected balance {_money(projection.minimum_balance)} in week {projection.minimum_balance_week}"],
    bars=recent, bars_caption="Weekly closing cash, latest weeks (ACTUAL)",
)
shortage_delta = f"week {projection.minimum_balance_week}" if projection.shortage_week is not None else "no breach projected"
ui.kpi_row([
    ("Minimum projected balance", _money(projection.minimum_balance),
     "Lowest deterministic FORECAST closing balance and week in the selected horizon."),
    ("Funding gap", _money(projection.funding_gap), "Forecast reserve shortfall plus the configured funding buffer."),
    ("Minimum reserve", _money(projection.reserve), "Editable reserve threshold for closing cash."),
    ("Runway", f"{runway:.1f} weeks" if runway is not None else "Not available",
     analysis.runway_weeks.reason or "Latest recorded cash divided by recent positive weekly burn."),
    ("Overdue receivables", _money(analysis.receivables_overdue), "Open invoice balances past due at the recorded-data snapshot."),
    ("DSO", f"{analysis.dso_days.value:.1f} days" if analysis.dso_days.value is not None else "Not available",
     analysis.dso_days.reason or "Computed days sales outstanding from recorded credit sales and open invoices."),
], deltas={"Minimum projected balance": shortage_delta})

dashboard_tab, guide_tab = st.tabs(["Dashboard", "How it works and my role"])
with dashboard_tab:
    main_col, side_col = st.columns([8, 4], gap="medium")
    with main_col, ui.card("cash", "Cash position", "Actual and forecast closing balance with the P10-P90 band and the reserve."):
        hero = charts.base_layout(x_title="Week starting", y_title="BDT", height=380)
        actual_x = [item.week_start.isoformat() for item in projection.actual_weeks]
        forecast_x = [item.week_start.isoformat() for item in projection.forecast_weeks]
        charts.line(hero, actual_x, [item.closing_balance for item in projection.actual_weeks],
                    layer="ACTUAL", name="Actual closing balance")
        charts.band(hero, forecast_x, uncertainty.p10, uncertainty.p90)
        charts.line(hero, forecast_x, [item.closing_balance for item in projection.forecast_weeks],
                    layer="FORECAST", name="Forecast closing balance")
        active_scenario = st.session_state.get("global-scenario-selector", "Forecast baseline")
        if active_scenario in lab.plans and active_scenario != "Option 0":
            scenario_points = lab.plans[active_scenario].balance_series_after
            charts.line(hero, [point.week_start for point in scenario_points],
                        [point.closing_balance for point in scenario_points], layer="HYPOTHETICAL",
                        name=f"{active_scenario} · HYPOTHETICAL")
        charts.reserve(hero, actual_x + forecast_x, projection.reserve)
        if projection.shortage_week is not None:
            marker_x = forecast_x[projection.shortage_week - 1]
            charts.shortage(hero, marker_x, forecast_x[-1])
            charts.shortage_marker(hero, marker_x, projection.forecast_weeks[projection.shortage_week - 1].closing_balance)
        st.plotly_chart(charts.polish(hero), width="stretch")
        ui.layer_legend()
        if active_scenario in lab.plans and active_scenario != "Option 0":
            st.caption(f"The {active_scenario} line is a Decision Lab scenario and remains HYPOTHETICAL.")
    with side_col:
        best = lab.plans[lab.best_plan_id]
        with ui.card("plan", "Recommended plan", lab.best_plan_reason if len(lab.best_plan_reason) < 140 else None):
            ui.plan_card(None, best.plan_id, [
                ("Remaining gap", _money(best.remaining_gap)),
                ("Modelled financing cost", _money(best.financing_cost)),
                ("Repayment capacity", f"{best.capacity_ratio:.2f}x" if best.capacity_ratio is not None else "Not available"),
                ("Scenario layer", ", ".join(best.layer_tags)),
            ], recommended=True)
            if best.pros:
                st.caption(best.pros[0])
            if "pages/lab.py" in visible_pages:
                if st.button("Open Decision Lab", type="primary", key="overview-open-lab", use_container_width=True):
                    st.switch_page("pages/lab.py")
            else:
                st.caption("Decision Lab is available to owner and finance_ops roles.")
        with ui.card("readiness", "Financing readiness", "Evidence-weighted indicator, not a loan approval prediction."):
            st.plotly_chart(charts.gauge(readiness.score, label=readiness.label), width="stretch")
            if readiness.missing_information:
                st.caption(f"Missing information: {len(readiness.missing_information)} item(s). See Financing for details.")

    aging_col, activity_col = st.columns([6, 6], gap="medium")
    with aging_col, ui.card("aging", "Receivables aging", "Overdue open receivables by days past due."):
        aging_fig = charts.base_layout(x_title="Days past due", y_title="BDT", height=300)
        aging_fig.add_bar(x=list(analysis.aging), y=list(analysis.aging.values()), marker_color=charts.PRIMARY,
                          hovertemplate="%{x}<br>BDT %{y:,.0f}<extra></extra>")
        aging_fig.update_layout(showlegend=False)
        st.plotly_chart(charts.polish(aging_fig), width="stretch")
        st.caption("Aging uses outstanding invoice balances and the latest transaction date. The 90+ bucket means more than 90 days.")
    with activity_col:
        with ui.card("approvals", "Pending approvals", "Submitted drafts waiting for owner review."):
            if user.role in {"owner", "finance_ops"}:
                try:
                    pending = list_drafts(user, status="pending_approval")
                    ui.activity_list(
                        [("clock", draft.action_type.replace("_", " ").title(), f"{draft.draft_id[:8]} · {draft.status}",
                          str(draft.created_at)[:10]) for draft in pending[:5]],
                        empty="No pending approvals.",
                    )
                except Exception:  # noqa: BLE001 - overview remains available if local draft storage is unavailable
                    st.info("Pending approval data is unavailable. Check the Approvals page.")
            else:
                st.caption("Pending draft details are not available for this role.")
        with ui.card("audit", "Latest audit events", "Most recent entries in the hash-chained audit log."):
            if can_user(user, "audit.view"):
                try:
                    events = get_audit_events(user, limit=5)
                    ui.activity_list([("file", str(row["action"]), str(row["entity"]), str(row["ts"])[:16]) for row in events],
                                     empty="No audit events yet.")
                except Exception:  # noqa: BLE001 - avoid showing local audit or database details
                    st.info("Audit events are unavailable. Check the Security page.")
            else:
                st.caption("Audit events are restricted to owner and auditor roles.")
with guide_tab:
    landing.how_it_works_signed_in(user, visible_pages)

ui.footer()
