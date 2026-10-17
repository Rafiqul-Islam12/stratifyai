"""Security - tiers, roles, controls and system status. Built in T11."""
from __future__ import annotations

import streamlit as st

from app import components as ui
from app.version import __version__

ui.load_styles()

ui.page_header(
    "Security",
    "Permission tiers, roles, controls and the state of this system.",
    business="Demo business",
)

ui.kpi_row(
    [
        ("Permission tiers", "4", "READ, DRAFT, APPROVAL_REQUIRED, MONEY_MOVEMENT."),
        ("Roles", "4", "owner, finance_ops, viewer, auditor."),
        ("Audit chain", "OK", "Hash-chained append-only log."),
        ("Demo data", "Synthetic", "No real company or personal data."),
    ],
    deltas={"Audit chain": "verified"},
)

st.caption("Sample data for layout review only - the security core is built in T11.")

ui.section_title("System status")
ui.kpi_row(
    [
        ("App version", f"v{__version__}", "Pinned in app/version.py."),
        ("Data mode", "Synthetic", "No real company or personal data."),
        ("Copilot mode", "Offline", "Answers come from computed results, never a model call."),
    ]
)

ui.section_title("Permission tiers")
tiers = [
    ("READ", "View data, dashboards and results", "All roles"),
    ("DRAFT", "Create scenarios and action drafts", "owner, finance_ops"),
    ("APPROVAL_REQUIRED", "Approve or reject drafts", "owner only"),
    ("MONEY_MOVEMENT", "Never executed by this system", "No role - always denied"),
]
ui.plan_row([(name, [("What", what), ("Who", who)], False) for name, what, who in tiers])

ui.section_title("Controls")
ui.empty_state(
    "Security core lands in T11",
    "Backend authorize() on every call, hash-chained audit with a verify function, safe errors and secret hygiene.",
    "Load demo business",
    disabled=True,
)

ui.footer()
