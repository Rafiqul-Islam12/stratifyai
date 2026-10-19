"""Historical business indicators and explainable receivables watchlist."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app import charts
from app import components as ui
from core.analysis import Metric, analyze
from core.loaders import load_case
from core.watchlist import receivables_watchlist

CASE_LABELS = {
    "stable_healthy": "Stable and healthy", "delayed_customer_payments": "Delayed customer payments",
    "high_expense_shortage": "High expense, shortage", "import_financing": "Import financing",
    "sales_drop_cost_rise": "Sales drop, cost rise",
}


def _money(value: float) -> str:
    return f"BDT {value:,.0f}"


def _metric(metric: Metric, suffix: str = "") -> str:
    if metric.value is None:
        return f"Not available: {metric.reason}"
    return f"{metric.value:,.1f}{suffix}"


ui.load_styles()
if ui.no_data_state("Business Analysis", "Recorded income, expenses and working capital."):
    st.stop()
active = st.session_state.get("active_synthetic_case", "high_expense_shortage")
case_name = ui.active_case("analysis-case-select")
case = load_case(case_name)
st.session_state["active_synthetic_case"] = case_name
st.session_state["synthetic_case_data"] = case
result = analyze(case)
watchlist = receivables_watchlist(case, as_of=result.as_of)

ui.page_header("Business Analysis", "Recorded income, expenses, working capital and explainable risk indicators.",
               business=case.profile.business_name, scenario=CASE_LABELS[case_name])
st.caption(f"Synthetic data · BDT · historical snapshot through {result.as_of.isoformat()}; no unsupported metric is estimated.")
ui.kpi_row([
    ("Recorded income", _money(result.income), f"Sum of recorded inflow transactions across {len(result.weekly)} weeks."),
    ("Recorded expenses", _money(result.expenses), "Sum of recorded outflow transactions."),
    ("Open receivables", _money(result.receivables_open), "Outstanding invoice amount after recorded payments."),
    ("Overdue receivables", _money(result.receivables_overdue), f"Open invoice amount due before {result.as_of.isoformat()}"),
    ("Overdue share", _metric(result.receivables_overdue_pct, "%"), "Overdue open receivables divided by total open receivables."),
    ("Payables due · 4 weeks", _money(result.payables_due_next_4_weeks), "Open bills due on or before 28 days from the snapshot."),
])
ui.kpi_row([
    ("Average weekly burn", _metric(result.burn_rate_weekly), "Positive net outflow across up to 13 recent recorded weeks; otherwise not available."),
    ("Runway", _metric(result.runway_weeks, " weeks"), "Latest recorded cash divided by positive recent weekly burn."),
    ("DSO", _metric(result.dso_days, " days"), result.dso_days.reason or "Computed from open receivables and credit sales."),
    ("DPO", _metric(result.dpo_days, " days"), result.dpo_days.reason or "Computed from open payables and identifiable purchase history."),
    ("Gross margin", _metric(result.gross_margin_pct, "%"), result.gross_margin_pct.reason or "Income less separately identified COGS/Inventory expense."),
    ("Top customer share", _metric(result.customer_concentration_pct, "%"), "Largest customer's share of total open receivables."),
])

tab_trends, tab_categories, tab_receivables, tab_insights = st.tabs(["Trends", "Categories", "Receivables", "Insights"])
with tab_trends:
    ui.section_title("Income and expenses by week")
    weekly = result.weekly[-26:]
    fig = charts.base_layout(title="Recorded weekly cash activity", x_title="Week starting", y_title="BDT", height=380)
    labels = [row["week_start"].isoformat() for row in weekly]
    charts.line(fig, labels, [row["income"] for row in weekly], layer="ACTUAL", name="Income")
    charts.line(fig, labels, [row["expenses"] for row in weekly], layer="ACTUAL", name="Expenses")
    st.plotly_chart(charts.polish(fig), width="stretch")

with tab_categories:
    def _category_card(column, key, title, rows):
        """Donut + progress rows for one category breakdown (top 6 plus an Other bucket)."""
        ordered = sorted(((name, amount) for name, amount in rows if amount > 0), key=lambda item: item[1], reverse=True)
        shown, rest = ordered[:6], ordered[6:]
        if rest:
            shown.append(("Other", sum(amount for _, amount in rest)))
        total = sum(amount for _, amount in shown) or 1.0
        with column, ui.card(key, title, f"Recorded total {_money(sum(amount for _, amount in ordered))}"):
            if not shown:
                st.caption("No recorded amounts in this category.")
                return
            st.plotly_chart(charts.donut([name for name, _ in shown], [amount for _, amount in shown],
                                         center=_money(total), height=280), width="stretch")
            ui.progress_rows([(name, _money(amount), amount / total * 100) for name, amount in shown])


    left, right = st.columns(2, gap="medium")
    _category_card(left, "income-by-category", "Income by category", result.income_by_category)
    _category_card(right, "expense-by-category", "Expenses by category", result.expense_by_category)

with tab_receivables:
    ui.section_title("Receivables aging")
    aging_fig = charts.base_layout(title="Overdue open receivables by age", y_title="BDT", height=320)
    aging_fig.add_bar(x=list(result.aging), y=list(result.aging.values()), marker_color=charts.PRIMARY)
    aging_fig.update_layout(showlegend=False)
    st.plotly_chart(charts.polish(aging_fig), width="stretch")
    st.caption("Aging is measured from due date to the latest transaction date. The 90+ bucket means more than 90 days.")

with tab_trends:
    ui.section_title("Monthly cash-flow trend")
    st.dataframe(pd.DataFrame([{"Month": row["month"], "Income (BDT)": round(row["income"], 2),
        "Expenses (BDT)": round(row["expenses"], 2), "Net cash flow (BDT)": round(row["net"], 2)}
        for row in result.monthly]), width="stretch", hide_index=True)
with tab_insights:
    ui.section_title("Computed insights and expense trend flags")
    for sentence in result.insights:
        st.markdown(f"- {sentence}")
    if not result.expense_trend_flags:
        st.caption("No expense category increased more than 15% in the latest four weeks versus the previous four recorded weeks.")

with tab_receivables:
    ui.section_title("Receivables watchlist")
    st.caption("Scores use overdue share (40), weighted days overdue (30), payment-delay trend (20) and customer concentration (10). Missing delay history is excluded and remaining weights are normalized.")
    if watchlist:
        st.dataframe(pd.DataFrame([{
            "Customer": row.customer_name, "Open (BDT)": round(row.open_balance, 2),
            "Overdue (BDT)": round(row.overdue_balance, 2), "Score": round(row.score, 1),
            "Status": row.label, "Invoice IDs": ", ".join(row.invoice_ids),
        } for row in watchlist]), width="stretch", hide_index=True)
        with st.expander("Watchlist score details"):
            for row in watchlist:
                st.markdown(f"**{row.customer_name} · {row.score:.1f} ({row.label})**")
                for name, score in row.component_scores.items():
                    st.markdown(f"- {name}: {f'{score:.1f} points' if score is not None else 'Not available'}")
                st.caption("Evidence invoices: " + (", ".join(row.invoice_ids) or "None"))
    else:
        ui.empty_state("No open receivables", "The watchlist appears when unpaid invoice balances are available.",
                       "Review data", disabled=True)
ui.footer()
