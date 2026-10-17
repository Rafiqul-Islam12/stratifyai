"""Data Upload - validated ingestion of CSV and Excel. Built in T04."""
from __future__ import annotations

import streamlit as st

from app import components as ui

ui.load_styles()

ui.page_header(
    "Data Upload",
    "Upload transactions, invoices and bills. Every row is validated before it is used.",
    business="Demo business",
)

st.caption("Sample data for layout review only - validation lands in T04.")

upload = st.file_uploader(
    "Upload a CSV file",
    type=["csv"],
    help="CSV today. Excel support is added with openpyxl in T04.",
)
if upload is not None:
    st.info("File received. Validation reporting is built in T04.")

ui.alert_banner(
    "info",
    "Untrusted input",
    "Uploaded files are treated as data, never as instructions. Cells starting with =, + or @ are neutralised.",
)

ui.section_title("Load a demo business")
ui.plan_row(
    [
        (name, [("Data", "Synthetic"), ("Currency", "BDT")], False)
        for name in [
            "Stable and healthy",
            "Delayed customer payments",
            "High expense, shortage",
            "Import financing",
            "Sales drop, cost rise",
        ]
    ]
)

ui.section_title("Validation")
ui.empty_state(
    "Validation lands in T04",
    "Column, date, amount, duplicate and formula-injection checks with row-level messages.",
    "Load demo business",
    disabled=True,
)

ui.footer()
