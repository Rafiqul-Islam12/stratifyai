"""Approvals and Audit - draft queue, approvals and the hash chain. Built in T11 and T12."""
from __future__ import annotations

import streamlit as st

from app import components as ui

ui.load_styles()

ui.page_header(
    "Approvals and Audit",
    "Review drafts, approve or reject them, and verify the audit chain.",
    business="Demo business",
)

ui.kpi_row(
    [
        ("Pending drafts", "3", "Drafts awaiting an owner decision."),
        ("Approved today", "1", "Drafts approved in the last 24 hours."),
        ("Audit entries", "1,204", "Total records in the chain."),
        ("Chain status", "OK", "Last verify_chain() result."),
    ],
    deltas={"Chain status": "verified"},
)

st.caption("Sample data for layout review only - the audit chain is built in T11.")

ui.alert_banner(
    "info",
    "Money movement is never executed",
    "The MONEY_MOVEMENT tier is denied for every role, including the owner, and is always logged.",
)

ui.section_title("Pending approvals")
ui.plan_card(
    st,
    "Collection reminder - 4 overdue customers",
    rows=[
        ("Type", "collection_reminder"),
        ("Amount", "BDT 385,000"),
        ("Status", "pending_approval"),
    ],
)

ui.section_title("Audit")
ui.empty_state(
    "Approvals and audit land in T11 and T12",
    "Pending queue, approve and reject dialogs, audit table with filters and a Verify chain button.",
    "Load demo business",
    disabled=True,
)

ui.footer()
