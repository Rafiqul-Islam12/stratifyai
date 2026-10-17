"""Draft creation, owner approval, simulated execution and audit history."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app import components as ui
from core.audit import verify_chain
from services.agent_actions import (
    InvalidTransition,
    create_draft,
    list_drafts,
    review_draft,
    simulate_execution,
    submit_draft,
)
from services.audit import get_audit_events, verify_audit_chain
from services.auth import current_user
from services.permissions import PermissionDenied, can_user


def _create_action_form(user) -> None:
    ui.section_title("Create an action draft")
    labels = {
        "collection_reminder": "Collection reminder",
        "supplier_deferral_request": "Supplier deferral request",
        "financing_application_pack": "Illustrative financing application pack",
    }
    action_type = st.selectbox("Draft type", list(labels), format_func=labels.get, key="agent-draft-type")
    fields = {}
    with st.form("agent-draft-form"):
        if action_type == "collection_reminder":
            fields["customer"] = st.text_input("Overdue customer")
            fields["invoice"] = st.text_input("Invoice reference")
            fields["amount"] = st.number_input("Overdue amount (BDT)", min_value=1.0, value=10000.0, step=1000.0)
            fields["due_date"] = st.text_input("Due date")
            fields["note"] = st.text_input("Optional note")
        elif action_type == "supplier_deferral_request":
            fields["supplier"] = st.text_input("Supplier")
            fields["invoice"] = st.text_input("Invoice reference")
            fields["amount"] = st.number_input("Payable amount (BDT)", min_value=1.0, value=10000.0, step=1000.0)
            fields["current_due_date"] = st.text_input("Current due date")
            fields["requested_due_date"] = st.text_input("Requested due date")
            fields["note"] = st.text_input("Optional note")
        else:
            fields["amount"] = st.number_input("Illustrative amount (BDT)", min_value=1.0, value=100000.0, step=10000.0)
            fields["purpose"] = st.text_input("Purpose")
            fields["repayment_plan"] = st.text_area("Repayment plan")
            fields["cash_flow_summary"] = st.text_area("Cash-flow summary")
            fields["readiness"] = st.text_area("Readiness summary")
        submitted = st.form_submit_button("Submit draft for owner approval", type="primary")
    if submitted:
        try:
            draft = create_draft(user, action_type, fields)
            submit_draft(user, draft.draft_id)
            st.success(f"Draft {draft.draft_id[:8]} submitted for owner review. Nothing was sent.")
            st.rerun()
        except (PermissionDenied, ValueError) as exc:
            st.error(str(exc))
        except Exception:  # noqa: BLE001 - keep local persistence details out of the UI
            st.error("The draft could not be saved. No external action was taken.")


@st.dialog("Review action draft")
def _review_dialog(user, draft_id: str, decision: str) -> None:
    verb = "approve" if decision == "approve" else "reject"
    st.write(f"Confirm that you want to {verb} draft `{draft_id[:8]}`.")
    comment = st.text_area("Owner review comment", key=f"review-comment-{draft_id}", max_chars=1000)
    if st.button(f"Confirm {verb}", type="primary", key=f"confirm-{decision}-{draft_id}"):
        try:
            review_draft(user, draft_id, decision, comment)
            st.session_state.pop("agent_review_dialog", None)
            st.rerun()
        except (PermissionDenied, InvalidTransition, KeyError, ValueError) as exc:
            st.error(str(exc))
        except Exception:  # noqa: BLE001 - keep persistence details out of the UI
            outcome = "approved" if decision == "approve" else "rejected"
            st.error(f"The draft could not be {outcome}. No external action was taken.")


def _render_owner_queue(user, drafts) -> None:
    ui.section_title("Pending approvals")
    reviewable = drafts
    if not reviewable:
        ui.empty_state("No pending drafts", "Submitted plans and action drafts will appear here for owner review.",
                       "Open Decision Lab", disabled=True)
        return
    selected_id = st.selectbox("Choose a draft", [draft.draft_id for draft in reviewable],
        format_func=lambda value: next(
            f"{draft.action_type.replace('_', ' ').title()} · {draft.draft_id[:8]} · {draft.status}"
            for draft in reviewable if draft.draft_id == value))
    draft = next(item for item in reviewable if item.draft_id == selected_id)
    st.json(draft.payload)
    if draft.review_comment:
        st.caption(f"Owner review comment: {draft.review_comment}")
    if draft.status == "pending_approval":
        approve_col, reject_col = st.columns(2)
        if approve_col.button("Approve draft", type="primary", key=f"approve-{draft.draft_id}"):
            st.session_state["agent_review_dialog"] = {"draft_id": draft.draft_id, "decision": "approve"}
        if reject_col.button("Reject draft", key=f"reject-{draft.draft_id}"):
            st.session_state["agent_review_dialog"] = {"draft_id": draft.draft_id, "decision": "reject"}
    elif draft.status == "approved":
        st.info("Approved by the owner. Simulated execution writes only to the local sandbox log.")
        if st.button("Record simulated execution", type="primary", key=f"execute-{draft.draft_id}"):
            try:
                simulate_execution(user, draft.draft_id)
                st.rerun()
            except (PermissionDenied, InvalidTransition, KeyError) as exc:
                st.error(str(exc))
            except Exception:  # noqa: BLE001 - no local error details in the UI
                st.error("The simulated execution could not be recorded.")
    else:
        st.info(f"This draft is {draft.status}; no further action is available.")
    st.markdown("**Status timeline**")
    st.dataframe(pd.DataFrame(draft.timeline), width="stretch", hide_index=True)
    pending_dialog = st.session_state.get("agent_review_dialog")
    if pending_dialog and pending_dialog.get("draft_id") == draft.draft_id:
        _review_dialog(user, draft.draft_id, pending_dialog["decision"])


ui.load_styles()
user = current_user()
if user is None:
    st.error("Sign in through the StratifyAI app to view this page.")
    st.stop()

ui.page_header("Approvals and Audit", "Create action drafts, review proposals and verify the audit trail.",
               business="Synthetic demo", scenario=f"Role: {user.role}")
can_audit = can_user(user, "audit.view")
chain = verify_chain() if can_audit else None
events = get_audit_events(user, limit=2000) if can_audit else []
drafts = list_drafts(user) if user.role in {"owner", "finance_ops"} else []
pending_count = sum(draft.status == "pending_approval" for draft in drafts)
ui.kpi_row([
    ("Pending approvals", str(pending_count) if user.role in {"owner", "finance_ops"} else "Restricted",
     "Pending items in the owner queue or your own drafts."),
    ("Audit entries", f"{len(events):,}" if can_audit else "Restricted", "Most recent audit entries."),
    ("Chain status", ("OK" if chain.ok else f"Broken · {chain.broken_index}") if chain else "Restricted",
     chain.message if chain else "Audit access is limited to owner and auditor roles."),
])
ui.alert_banner("info", "Money movement is always denied",
                "No user, including the owner, can move or transmit money through this application.")

if user.role == "owner":
    _render_owner_queue(user, drafts)
elif user.role == "auditor":
    ui.section_title("Approval status")
    st.info("Auditor access is read-only and does not expose draft contents.")
else:
    ui.section_title("Your drafts")
    own_drafts = [draft for draft in drafts if draft.created_by == user.username]
    if own_drafts:
        st.dataframe(pd.DataFrame([{"Draft": draft.draft_id[:8], "Type": draft.action_type,
            "Status": draft.status, "Created": draft.created_at} for draft in own_drafts]),
            width="stretch", hide_index=True)
    else:
        st.caption("You have not submitted any drafts yet.")
    if own_drafts:
        selected_own_id = st.selectbox("Draft details", [draft.draft_id for draft in own_drafts],
            format_func=lambda value: next(
                f"{draft.action_type.replace('_', ' ').title()} · {draft.draft_id[:8]} · {draft.status}"
                for draft in own_drafts if draft.draft_id == value), key="own-draft-details")
        selected_own = next(draft for draft in own_drafts if draft.draft_id == selected_own_id)
        st.json(selected_own.payload)
        st.markdown("**Status timeline**")
        st.dataframe(pd.DataFrame(selected_own.timeline), width="stretch", hide_index=True)

if user.role in {"owner", "finance_ops"}:
    _create_action_form(user)

if can_audit:
    ui.section_title("Audit log")
    filters = st.columns(3)
    actor_filter = filters[0].text_input("Filter actor")
    audit_actions = sorted({row["action"] for row in events})
    selected_audit_action = filters[1].selectbox("Filter action", ["All", *audit_actions])
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
            action=selected_audit_action if selected_audit_action != "All" else None, limit=int(limit))
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
