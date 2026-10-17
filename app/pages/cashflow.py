"""Cash Flow - forecast, reserve and shortage alerts. Built in T05."""
from __future__ import annotations

import streamlit as st

from app import charts
from app import components as ui

ui.load_styles()

ui.page_header(
    "Cash Flow",
    "Weekly cash forecast, minimum reserve and the first shortage week.",
    business="Demo business",
)

ui.kpi_row(
    [
        ("Opening cash", "BDT 1,250,000", "Latest recorded balance."),
        ("Horizon", "13 wks", "Forecast length, minimum 8 weeks."),
        ("Reserve", "BDT 650,000", "Minimum balance the business keeps."),
        ("First shortage", "W7", "First week closing below the reserve."),
    ]
)

st.caption("Sample data for layout review only - real values are computed in T05.")

x = [f"W{i}" for i in range(1, 11)]
fig = charts.base_layout(title="Cash balance (placeholder data)", x_title="Week", y_title="BDT")
charts.line(fig, x, [1250, 1180, 1090, 980, 900, 810, 720, 640, 560, 490], layer="ACTUAL", name="Actual")
charts.line(fig, x, [None, 1180, 1090, 980, 870, 760, 660, 570, 490, 420], layer="FORECAST", name="Forecast")
charts.reserve(fig, x, 650)
charts.shortage_marker(fig, "W7", 660)
st.plotly_chart(fig, use_container_width=True)
ui.layer_legend()

ui.section_title("Forecast")
ui.empty_state(
    "Forecast engine lands in T05",
    "Shortage detection, severity, weekly table and a configurable reserve.",
    "Load demo business",
    disabled=True,
)

ui.footer()
