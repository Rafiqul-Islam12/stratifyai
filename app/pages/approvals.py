"""Owner approval placeholder and permission-checked append-only audit view."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app import components as ui
from core.audit import verify_chain
from services.audit import get_audit_events, verify_audit_chain
from services.auth import current_user
from services.permissions import PermissionDenied

ui.load_styles()
user = current_user()
if user is None:
    st.error("Sign in through the StratifyAI app to view this page.")
    st.stop()

ui.page_header("Approvals and Audit", "Review the audit trail and verify its integrity.",
               business="Synthetic demo", scenario=f"Role: {user.role}")
chain = verify_chain()
events = get_audit_events(user, limit=2000)
ui.kpi_row([
    ("Pending approvals", "T12", "Draft review workflow is added in the next security workflow task."),
    ("Audit entries", f"{len(events):,}", "Most recent entries returned by the audit log."),
    ("Chain status", "OK" if chain.ok else f"Broken · {chain.broken_index}", chain.message),
])
ui.alert_banner("info", "Money movement is always denied",
                "No user, including the owner, can move or transmit money through this application.")

ui.section_title("Pending approvals")
if user.role == "owner":
    ui.empty_state("No pending drafts", "Draft creation and owner review actions are built in T12.",
                   "Open Decision Lab", disabled=True)
else:
    st.info("Pending approval details are visible to the owner only. Auditor access is read-only for the audit log.")

ui.section_title("Audit log")
filters = st.columns(3)
actor_filter = filters[0].text_input("Filter actor")
actions = sorted({row["action"] for row in events})
selected_action = filters[1].selectbox("Filter action", ["All", *actions])
limit = filters[2].selectbox("Rows", (50, 100, 500, 2000), index=1)
if st.button("Verify chain", type="primary", key="audit-verify"):
    try:
        chain = verify_audit_chain(user)
        st.session_state["audit_verification"] = chain
    except PermissionDenied as exc:
        st.error(str(exc))
    except Exception:  # noqa: BLE001 - expose only a safe audit failure message
        st.error("Audit verification failed safely. Review the system status for the chain result.")
    else:
        ui.alert_banner("info" if chain.ok else "critical", "Audit chain verified" if chain.ok else "Audit chain broken", chain.message)
try:
    filtered = get_audit_events(user, actor=actor_filter or None,
        action=selected_action if selected_action != "All" else None, limit=int(limit))
    if filtered:
        st.dataframe(pd.DataFrame([{key: row[key] for key in
            ("id", "ts", "actor", "role", "action", "entity", "payload_json", "hash")} for row in filtered]),
            width="stretch", hide_index=True)
    else:
        ui.empty_state("No matching audit entries", "Change the filters or perform a logged action.",
                       "Clear filters", disabled=True)
except PermissionDenied as exc:
    st.error(str(exc))
except Exception:  # noqa: BLE001 - expose only a safe audit loading message
    st.error("The audit entries could not be loaded. Sensitive error details are not shown.")
ui.footer()
