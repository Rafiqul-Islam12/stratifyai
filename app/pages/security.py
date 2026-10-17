"""Live security controls, permission registry and local system status."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from app import components as ui
from app.version import __version__
from core.audit import verify_chain
from services.auth import current_user
from services.permissions import permission_matrix

ROOT = Path(__file__).resolve().parents[2]


def _doc_bullets(section: str) -> list[str]:
    document = (ROOT / "docs" / "SECURITY.md").read_text(encoding="utf-8")
    marker = f"## {section}"
    if marker not in document:
        return []
    content = document.split(marker, 1)[1].split("\n## ", 1)[0]
    return [line[2:].strip() for line in content.splitlines() if line.startswith("- ")]

ui.load_styles()
user = current_user()
if user is None:
    st.error("Sign in through the StratifyAI app to view this page.")
    st.stop()
chain = verify_chain()
test_summary = "Not available (no evidence/test_results.txt file)."
test_file = ROOT / "evidence" / "test_results.txt"
if test_file.is_file():
    try:
        test_summary = test_file.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-1][:240]
    except (OSError, IndexError):
        test_summary = "Not available (test summary could not be read)."
fonts_local = any((ROOT / "static" / "fonts").glob("*.woff2"))

ui.page_header("Security", "Permission registry, audit status and system controls.",
               business="Synthetic demo", scenario=f"Signed in: {user.display_name} · {user.role}")
st.caption("DEMO authentication. This application uses synthetic data and does not execute money movement.")

ui.section_title("System status")
ui.kpi_row([
    ("App version", f"v{__version__}", "Version loaded from app/version.py."),
    ("Data mode", "Synthetic", "Demo data only."),
    ("Copilot mode", os.getenv("COPILOT_MODE", "offline").lower(), "Local mode from environment; default is offline."),
])
ui.kpi_row([
    ("Audit chain", "OK" if chain.ok else f"Broken · {chain.broken_index}", chain.message),
    ("Last test run", test_summary, "Last line of evidence/test_results.txt when available."),
    ("Fonts local", "Yes" if fonts_local else "No", "Checks static/fonts for a local WOFF2 font file."),
])

ui.section_title("Permission tiers")
tiers = [
    ("READ", "View data, dashboards and results", "All roles or the action-specific read scope"),
    ("DRAFT", "Run scenarios, upload and create drafts", "owner, finance_ops"),
    ("APPROVAL_REQUIRED", "Approve or reject; simulated execution", "owner only"),
    ("MONEY_MOVEMENT", "Transmit or move money", "No role; always denied and audited"),
]
st.dataframe(pd.DataFrame(tiers, columns=("Tier", "Action", "Allowed role scope")), width="stretch", hide_index=True)

ui.section_title("Role preview from the backend registry")
st.dataframe(pd.DataFrame(permission_matrix()), width="stretch", hide_index=True)
ui.section_title("Controls")
for control in _doc_bullets("Controls (baseline)"):
    st.markdown(f"- {control}")
ui.section_title("Known risks")
for risk in _doc_bullets("Known risks (initial list; keep honest and extend)"):
    st.markdown(f"- {risk}")

ui.footer()
