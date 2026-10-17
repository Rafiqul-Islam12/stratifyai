"""Liquidity Decision Lab - the flagship comparison. Built in T07 and T08."""
from __future__ import annotations

import streamlit as st

from app import charts
from app import components as ui

ui.load_styles()

ui.page_header(
    "Liquidity Decision Lab",
    "Compare four ways to close a cash gap: do nothing, optimise, partial financing, full financing.",
    business="Demo business",
)

ui.kpi_row(
    [
        ("Funding gap", "BDT 240,000", "Reserve minus the lowest projected balance."),
        ("Shortage week", "W7", "First week below the reserve."),
        ("Recommended plan", "Option A", "Feasible plan with the lowest total cost."),
    ]
)

st.caption("Sample data for layout review only - plans are computed in T07.")

plans = [
    ("Option 0 - Do nothing", "BDT 650,000", "BDT 240,000", "W7", False),
    ("Option A - Collect & optimise", "BDT 480,000", "BDT 70,000", "W10", True),
    ("Option B - Partial financing", "BDT 690,000", "BDT 0", "None", False),
    ("Option C - Full financing", "BDT 900,000", "BDT 0", "None", False),
]
ui.plan_row(
    [
        (name, [("Best balance", best), ("Remaining gap", gap), ("Shortage", week)], recommended)
        for name, best, gap, week, recommended in plans
    ]
)

x = [f"W{i}" for i in range(1, 11)]
fig = charts.base_layout(title="Plan comparison (placeholder data)", x_title="Week", y_title="BDT")
charts.line(fig, x, [1250, 1180, 1090, 980, 870, 760, 660, 570, 490, 420], layer="FORECAST", name="Option 0")
charts.line(fig, x, [1250, 1180, 1290, 1180, 1120, 1010, 880, 790, 720, 660], layer="HYPOTHETICAL", name="Option A")
charts.line(fig, x, [1250, 1330, 1300, 1350, 1310, 1330, 1290, 1310, 1270, 1290], layer="HYPOTHETICAL", name="Option B")
charts.reserve(fig, x, 650)
st.plotly_chart(fig, use_container_width=True)
ui.layer_legend()

ui.section_title("Decision Lab")
ui.empty_state(
    "Lab content lands in T07 and T08",
    "Isolated L1/L2/L3 levers, per-plan cost and capacity, sliders, stress tests and saved scenarios.",
    "Open Overview",
    disabled=True,
)

ui.footer()
