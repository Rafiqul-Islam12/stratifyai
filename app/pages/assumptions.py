"""Assumptions - editable defaults behind every calculation. Built in T08."""
from __future__ import annotations

import streamlit as st

from app import components as ui

ui.load_styles()

ui.page_header(
    "Assumptions",
    "Every default used by the forecast, the levers and the financing templates.",
    business="Demo business",
)

st.caption("Sample values for layout review only - editable in T08.")

ui.alert_banner(
    "warning",
    "Illustrative values",
    "These are starting points, not rules. Financing terms are templates, not real lender offers.",
)

ui.section_title("Forecast")
columns = st.columns(3)
columns[0].slider("Minimum reserve (BDT)", 0, 1_000_000, 650_000, step=10_000)
columns[1].slider("Horizon (weeks)", 8, 13, 13)
columns[2].slider("Funding buffer (%)", 0, 30, 0)

ui.section_title("Decision Lab levers")
columns = st.columns(3)
columns[0].slider("L1 - collect overdue (%)", 0, 100, 50)
columns[1].slider("L2 - defer payables (weeks)", 0, 8, 2)
columns[2].slider("L3 - cut discretionary (%)", 0, 50, 10)

ui.section_title("Stress tests")
columns = st.columns(3)
columns[0].slider("Sales change (%)", -50, 0, -20)
columns[1].slider("Shipping and other costs (%)", 0, 50, 15)
columns[2].slider("FX shock (%)", -30, 30, 0)

ui.section_title("Assumptions")
ui.empty_state(
    "Assumption store lands in T08",
    "Validated ranges, a reset button and every value visible in one place.",
    "Load demo business",
    disabled=True,
)

ui.footer()
