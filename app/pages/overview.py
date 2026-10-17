"""Overview - everything at a glance. Content is built in T14."""
from __future__ import annotations

import streamlit as st

from app import charts
from app import components as ui

ui.load_styles()

ui.page_header(
    "Overview",
    "Business health, cash forecast and the recommended plan in one view.",
    business="Demo business",
)

ui.kpi_row(
    [
        ("Current cash", "BDT 1,250,000", "Latest recorded balance."),
        ("Min projected balance", "BDT 410,000", "Lowest closing balance in the forecast horizon."),
        ("Funding gap", "BDT 240,000", "Reserve minus the lowest projected balance, plus buffer."),
        ("Runway", "6 wks", "Weeks until the balance falls below the reserve."),
        ("Overdue receivables", "BDT 385,000", "Invoices past their due date."),
        ("DSO", "41.2 days", "Average days from invoice date to collection."),
    ],
    deltas={"Min projected balance": "week 6"},
)

# Placeholder chart - no business logic here, so the numbers are illustrative.
x = ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10"]
fig = charts.base_layout(title="Projected cash balance (placeholder data)", x_title="Week", y_title="BDT")
charts.line(fig, x, [1250, 1180, 1090, 980, 900, 810, 720, 640, 560, 490], layer="ACTUAL", name="Actual")
charts.line(fig, x, [None, 1180, 1090, 980, 870, 760, 660, 570, 490, 420], layer="FORECAST", name="Forecast")
charts.band(fig, x, [None] * 4 + [790, 690, 590, 490, 410, 350], [None] * 4 + [950, 830, 730, 650, 570, 490])
charts.reserve(fig, x, 650)
st.plotly_chart(fig, use_container_width=True)
ui.layer_legend()

ui.section_title("Sections")
ui.empty_state(
    "Overview content lands in T14",
    "Alert banner, hero chart, recommended plan, readiness, aging, approvals and audit.",
    "Open the Decision Lab",
    disabled=True,
)

ui.footer()
