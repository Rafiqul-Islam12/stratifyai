"""Business Analysis - reliable indicators and the receivables watchlist. Built in T10."""
from __future__ import annotations

import streamlit as st

from app import charts
from app import components as ui

ui.load_styles()

ui.page_header(
    "Business Analysis",
    "Income, expenses, receivables, payables and the indicators that can be computed reliably.",
    business="Demo business",
)

ui.kpi_row(
    [
        ("Income (8 wks)", "BDT 4,820,000", "Weekly run-rate sales."),
        ("Expenses (8 wks)", "BDT 3,910,000", "Sum of outflow categories."),
        ("Receivables", "BDT 1,240,000", "Open invoices."),
        ("Payables due", "BDT 460,000", "Bills due in the next 4 weeks."),
        ("Burn rate", "BDT 114,000", "Average weekly net cash outflow."),
        ("Runway", "6 wks", "Cash divided by burn rate."),
    ]
)

st.caption("Sample data for layout review only - metrics are computed in T10.")

x = [f"W{i}" for i in range(1, 9)]
fig = charts.base_layout(title="Income and expenses (placeholder data)", x_title="Week", y_title="BDT")
charts.line(fig, x, [610, 640, 590, 620, 660, 610, 640, 1150], layer="ACTUAL", name="Income")
charts.line(fig, x, [500, 480, 520, 490, 510, 500, 480, 930], layer="ACTUAL", name="Expenses")
st.plotly_chart(fig, use_container_width=True)

ui.section_title("Analysis")
ui.empty_state(
    "Analysis content lands in T10",
    "Aging buckets, trends, gross margin when COGS exists, and the explainable receivables watchlist.",
    "Load demo business",
    disabled=True,
)

ui.footer()
