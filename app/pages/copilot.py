"""Copilot - grounded answers with an evidence receipt. Built in T13."""
from __future__ import annotations

import streamlit as st

from app import components as ui

ui.load_styles()

ui.page_header(
    "Copilot",
    "Ask questions about the forecast and the plans. Every answer cites its evidence.",
    business="Demo business",
)

st.caption("Sample data for layout review only - the copilot is built in T13.")

ui.alert_banner(
    "warning",
    "Offline mode",
    "The copilot explains computed results and never invents numbers. Uploaded text is treated as data, not instructions.",
)

ui.section_title("Try asking")
ui.plan_row(
    [
        (question, [("Mode", "Offline"), ("Evidence", "E1, E3, E7"), ("Validator", "passed")], False)
        for question in [
            "Why will I run short of cash?",
            "How much funding do I need?",
            "Compare the four plans",
        ]
    ]
)

ui.section_title("Copilot")
ui.empty_state(
    "Copilot lands in T13",
    "Evidence pack, deterministic router, injection defence, output validator and a receipt under every answer.",
    "Open Overview",
    disabled=True,
)

ui.footer()
