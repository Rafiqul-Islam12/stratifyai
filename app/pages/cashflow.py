"""Cash Flow page backed by the deterministic weekly forecast engine."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app import charts
from app import components as ui
from core.forecast import ForecastResult, forecast
from core.loaders import load_case
from core.montecarlo import MonteCarloResult, simulate

CASE_LABELS = {
    "stable_healthy": "Stable and healthy",
    "delayed_customer_payments": "Delayed customer payments",
    "high_expense_shortage": "High expense, shortage",
    "import_financing": "Import financing",
    "sales_drop_cost_rise": "Sales drop, cost rise",
}


def _money(value: float) -> str:
    return f"BDT {value:,.0f}"


@st.cache_data(show_spinner=False)
def _cached_simulation(case, projection, cv: float, delay_sd: float) -> MonteCarloResult:
    return simulate(case, projection=projection, sales_variability_cv=cv,
                    customer_delay_sd_days=delay_sd)


def _alert(result: ForecastResult, uncertainty: MonteCarloResult) -> tuple[str, str, str]:
    probability_week = (result.shortage_week - 1) if result.shortage_week else max(
        range(len(uncertainty.probability_below_reserve)), key=uncertainty.probability_below_reserve.__getitem__)
    probability = uncertainty.probability_below_reserve[probability_week]
    probability_text = f"Computed chance of falling below reserve in week {probability_week + 1}: {probability:.1%}."
    if result.shortage_week is None:
        return "info", "No projected reserve breach", f"The P50 closing balance stays at or above reserve. {probability_text}"
    when = result.shortage_date.isoformat() if result.shortage_date else ""
    week_detail = f"Week {result.shortage_week} ({when})"
    if result.severity == "critical":
        return (
            "critical",
            "Projected cash falls below zero",
            f"The first reserve breach is {week_detail}; the forecast also falls below zero in week {result.below_zero_week}. {probability_text}",
        )
    return (
        "warning",
        "Projected reserve breach",
        f"The first reserve breach is {week_detail}. The minimum projected balance is {_money(result.minimum_balance)}. {probability_text}",
    )


ui.load_styles()
if ui.no_data_state("Cash Flow", "Weekly actuals, forecast and reserve risk."):
    st.stop()
case_name = ui.active_case("cashflow-case-select")
case_data = load_case(case_name)
st.session_state["active_synthetic_case"] = case_name
st.session_state["synthetic_case_data"] = case_data

ui.page_header(
    "Cash Flow",
    "Weekly actuals, a deterministic cash forecast, and the first reserve breach.",
    business=case_data.profile.business_name,
    scenario=CASE_LABELS[case_name],
)

ctrl_reserve, ctrl_cv = st.columns(2, gap="medium")
default_result = forecast(case_data)
reserve_value = ctrl_reserve.number_input(
    "Minimum cash reserve (BDT)",
    min_value=0,
    value=max(0, round(default_result.reserve)),
    step=10_000,
    key=f"cashflow-reserve-{case_name}",
    help="Default reserve equals the configured reserve weeks multiplied by average fixed weekly outflows.",
)
result = forecast(case_data, reserve=float(reserve_value))
variability = ctrl_cv.slider("Sales variability (CV)", 0.0, 1.0,
    float(case_data.assumptions.sales_variability_cv), step=0.05,
    help="Coefficient of variation for weekly cash receipts; raise it to widen the uncertainty band.")
uncertainty = _cached_simulation(case_data, result, float(variability), float(case_data.assumptions.customer_delay_sd_days))
st.session_state["cash_flow_forecast"] = result
st.session_state["cash_flow_uncertainty"] = uncertainty
tone, title, body = _alert(result, uncertainty)
ui.alert_banner(tone, title, body)

first_shortage = f"Week {result.shortage_week}" if result.shortage_week is not None else "None"
ui.kpi_row(
    [
        ("Opening cash", _money(result.opening_cash), "Latest recorded transaction balance."),
        ("Forecast horizon", f"{result.horizon_weeks} weeks", "Weekly deterministic forecast horizon."),
        ("Minimum reserve", _money(result.reserve), "Editable reserve threshold for closing cash."),
        ("First shortage", first_shortage, "First forecast week with closing cash below the reserve."),
    ]
)
ui.kpi_row(
    [
        ("Minimum projected balance", _money(result.minimum_balance), f"Forecast week {result.minimum_balance_week}."),
        ("Funding gap", _money(result.funding_gap), f"Includes a {result.funding_buffer_pct:g}% optional buffer."),
        ("Below-zero week", f"Week {result.below_zero_week}" if result.below_zero_week is not None else "None", "First forecast closing balance below zero."),
        ("Fixed weekly outflow", _money(result.fixed_weekly_outflow), "Average non-discretionary outflow over the recent eight weeks."),
    ]
)

tab_forecast, tab_table, tab_assumptions = st.tabs(["Forecast", "Weekly table", "Assumptions"])
with tab_forecast:
    ui.section_title("Cash balance")
    figure = charts.base_layout(title="Actual and forecast cash balance", x_title="Week starting", y_title="BDT", height=420)
    actual_x = [week.week_start.isoformat() for week in result.actual_weeks]
    forecast_x = [week.week_start.isoformat() for week in result.forecast_weeks]
    charts.line(figure, actual_x, [week.closing_balance for week in result.actual_weeks], layer="ACTUAL", name="Actual closing balance")
    charts.line(figure, forecast_x, [week.closing_balance for week in result.forecast_weeks], layer="FORECAST", name="Forecast closing balance")
    charts.band(figure, forecast_x, uncertainty.p10, uncertainty.p90)
    charts.reserve(figure, actual_x + forecast_x, result.reserve)
    if result.shortage_week is not None:
        breach_x = forecast_x[result.shortage_week - 1]
        charts.shortage(figure, breach_x, forecast_x[-1])
        charts.shortage_marker(figure, breach_x, result.forecast_weeks[result.shortage_week - 1].closing_balance)
    st.plotly_chart(charts.polish(figure), width="stretch")
    ui.layer_legend()

with tab_table:
    ui.section_title("Weekly cash table")
    table_rows = [
        {
            "Week starting": row.week_start.isoformat(),
            "Layer": row.layer,
            "Inflow (BDT)": round(row.inflow, 2),
            "Outflow (BDT)": round(row.outflow, 2),
            "Net (BDT)": round(row.net, 2),
            "Closing (BDT)": round(row.closing_balance, 2),
        }
        for row in result.weeks
    ]
    st.dataframe(pd.DataFrame(table_rows), width="stretch", hide_index=True)

with tab_assumptions:
    ui.section_title("Forecast assumptions")
    delay_values = list(result.payment_delay_days.values())
    if delay_values:
        delay_summary = f"{len(delay_values)} customer delay assumptions; range {min(delay_values):g} to {max(delay_values):g} days."
    else:
        delay_summary = "No customer delay assumptions; the expected delay defaults to zero days."
    st.markdown(
        f"- Reserve basis: {case_data.assumptions.minimum_reserve_weeks:g} weeks of average fixed outflows.\n"
        f"- Fixed weekly outflow estimate: {_money(result.fixed_weekly_outflow)} from the most recent eight weeks.\n"
        f"- Customer payment timing: {delay_summary}\n"
        "- Run-rate categories covered by receivables or payables are excluded from recurring projections."
    )
ui.footer()
