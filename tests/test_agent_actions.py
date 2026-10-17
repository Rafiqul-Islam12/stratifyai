"""T12 agent draft state machine and human-controlled execution tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.audit import list_events
from services.agent_actions import (
    InvalidTransition,
    create_draft,
    confirmed_plans,
    get_draft,
    list_drafts,
    review_draft,
    simulate_execution,
    submit_draft,
)
from services.auth import AUTH_SESSION_KEY, DEMO_PASSWORD_DEFAULTS, login, login_demo
from services.permissions import PermissionDenied


@pytest.fixture
def stores(tmp_path, monkeypatch):
    db_path = tmp_path / "agent_actions.sqlite3"
    sandbox = tmp_path / "sandbox_log.jsonl"
    monkeypatch.setenv("STRATIFY_AGENT_ACTIONS_DB", str(db_path))
    monkeypatch.setenv("STRATIFY_AUDIT_DB", str(db_path))
    monkeypatch.setenv("STRATIFY_SANDBOX_LOG", str(sandbox))
    return db_path, sandbox


def _user(role: str, db_path):
    state = {}
    return login(role, DEMO_PASSWORD_DEFAULTS[role], session_state=state, db_path=db_path)


def test_structured_action_templates_escape_untrusted_text(stores):
    db_path, _ = stores
    finance = _user("finance_ops", db_path)
    reminder = create_draft(finance, "collection_reminder", {
        "customer": "<script>alert(1)</script>", "invoice": "INV-7", "amount": 1250,
        "due_date": "2026-10-01", "note": "please call",
    }, db_path=db_path)
    assert reminder.status == "draft"
    assert "<script>" not in reminder.payload["message_preview"]
    assert "&lt;script&gt;" in reminder.payload["message_preview"]

    supplier = create_draft(finance, "supplier_deferral_request", {
        "supplier": "Supplier A", "invoice": "BILL-8", "amount": 2500,
        "current_due_date": "2026-10-01", "requested_due_date": "2026-10-15",
    }, db_path=db_path)
    pack = create_draft(finance, "financing_application_pack", {
        "amount": 50000, "purpose": "Working capital", "repayment_plan": "Monthly",
        "cash_flow_summary": "13-week forecast", "readiness": "Illustrative only",
    }, db_path=db_path)
    proposal = create_draft(finance, "plan_proposal", {
        "case_name": "case-a", "plan_id": "Option A", "plan_snapshot": {"funding_gap": 1000},
    }, db_path=db_path)
    assert supplier.payload["execution_policy"] == "manual review only"
    assert pack.payload["execution_policy"] == "draft only; no application is submitted"
    assert proposal.payload["assumptions_layer"] == "HYPOTHETICAL"


def test_owner_approval_rejection_and_execution_are_idempotent(stores):
    db_path, sandbox = stores
    finance = _user("finance_ops", db_path)
    owner = _user("owner", db_path)
    proposal = create_draft(finance, "plan_proposal", {
        "case_name": "high_expense_shortage", "plan_id": "Option A",
        "plan_snapshot": {"balance_series_after": [{"week_start": "2026-10-01", "closing_balance": 500}]},
    }, db_path=db_path)
    pending = submit_draft(finance, proposal.draft_id, db_path=db_path)
    assert pending.status == "pending_approval"
    assert submit_draft(finance, proposal.draft_id, db_path=db_path).status == "pending_approval"

    approved = review_draft(owner, proposal.draft_id, "approve", "Owner confirmed this plan.", db_path=db_path)
    assert approved.status == "approved"
    assert approved.payload["assumptions_layer"] == "CONFIRMED"
    assert confirmed_plans(finance, "high_expense_shortage", db_path=db_path) == [approved.payload]
    assert review_draft(owner, proposal.draft_id, "approve", "duplicate", db_path=db_path).status == "approved"

    executed = simulate_execution(owner, proposal.draft_id, db_path=db_path, sandbox_log=sandbox)
    assert executed.status == "simulated_executed"
    assert simulate_execution(owner, proposal.draft_id, db_path=db_path, sandbox_log=sandbox).status == "simulated_executed"
    entries = [json.loads(line) for line in sandbox.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 1
    assert entries[0]["network_sent"] is False
    events = [row["action"] for row in list_events(db_path=db_path)]
    assert events.count("draft.approved") == 1
    assert events.count("execution.simulated") == 1

    rejected = create_draft(finance, "collection_reminder", {
        "customer": "Customer", "invoice": "INV-9", "amount": 500, "due_date": "2026-10-02",
    }, db_path=db_path)
    submit_draft(finance, rejected.draft_id, db_path=db_path)
    assert review_draft(owner, rejected.draft_id, "reject", "Needs revision.", db_path=db_path).status == "rejected"
    assert review_draft(owner, rejected.draft_id, "reject", db_path=db_path).status == "rejected"
    with pytest.raises(InvalidTransition):
        simulate_execution(owner, rejected.draft_id, db_path=db_path, sandbox_log=sandbox)


def test_roles_and_transition_rules_are_enforced_and_audited(stores):
    db_path, sandbox = stores
    finance = _user("finance_ops", db_path)
    viewer = _user("viewer", db_path)
    owner = _user("owner", db_path)
    draft = create_draft(finance, "collection_reminder", {
        "customer": "Customer", "invoice": "INV-1", "amount": 100, "due_date": "2026-10-01",
    }, db_path=db_path)
    with pytest.raises(PermissionDenied):
        create_draft(viewer, "collection_reminder", {
            "customer": "Customer", "invoice": "INV-2", "amount": 100, "due_date": "2026-10-01",
        }, db_path=db_path)
    with pytest.raises(PermissionDenied):
        review_draft(finance, draft.draft_id, "approve", db_path=db_path)
    with pytest.raises(InvalidTransition):
        simulate_execution(owner, draft.draft_id, db_path=db_path, sandbox_log=sandbox)
    assert list_drafts(finance, db_path=db_path) == [draft]
    with pytest.raises(PermissionDenied):
        list_drafts(viewer, db_path=db_path)
    with pytest.raises(PermissionDenied):
        simulate_execution(viewer, draft.draft_id, db_path=db_path, sandbox_log=sandbox)


def test_full_finance_ops_to_owner_ui_flow(monkeypatch, stores):
    db_path, sandbox = stores
    finance = login_demo("finance_ops", session_state={}, db_path=db_path)
    main_path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    finance_app = AppTest.from_file(main_path, default_timeout=30)
    finance_app.session_state[AUTH_SESSION_KEY] = finance._session_token
    finance_app.run().switch_page("pages/approvals.py").run()
    assert not finance_app.exception
    for label, value in (("Overdue customer", "Customer Demo"), ("Invoice reference", "INV-UI-1"),
                         ("Due date", "2026-10-01")):
        next(widget for widget in finance_app.text_input if widget.label == label).set_value(value)
    next(button for button in finance_app.button if button.label == "Submit draft for owner approval").click().run()
    assert not finance_app.exception
    draft = next(item for item in list_drafts(finance, db_path=db_path) if item.action_type == "collection_reminder")

    owner = login_demo("owner", session_state={}, db_path=db_path)
    owner_app = AppTest.from_file(main_path, default_timeout=30)
    owner_app.session_state[AUTH_SESSION_KEY] = owner._session_token
    owner_app.run().switch_page("pages/approvals.py").run()
    assert not owner_app.exception
    next(button for button in owner_app.button if button.key == f"approve-{draft.draft_id}").click().run()
    assert not owner_app.exception
    assert get_draft(owner, draft.draft_id, db_path=db_path).status == "approved"
    next(button for button in owner_app.button if button.key == f"execute-{draft.draft_id}").click().run()
    assert not owner_app.exception
    assert get_draft(owner, draft.draft_id, db_path=db_path).status == "simulated_executed"
    assert len(sandbox.read_text(encoding="utf-8").splitlines()) == 1

    finance_app.switch_page("pages/lab.py").run()
    assert not finance_app.exception
    proposal_button = next(button for button in finance_app.button if button.key == "lab-proposal-save-high_expense_shortage")
    proposal_button.click().run()
    assert not finance_app.exception
    plan_draft = next(item for item in list_drafts(finance, db_path=db_path) if item.action_type == "plan_proposal")

    owner_app.switch_page("pages/approvals.py").run()
    next(widget for widget in owner_app.selectbox if widget.label == "Choose a draft").set_value(plan_draft.draft_id).run()
    next(button for button in owner_app.button if button.key == f"approve-{plan_draft.draft_id}").click().run()
    assert not owner_app.exception
    assert get_draft(owner, plan_draft.draft_id, db_path=db_path).payload["assumptions_layer"] == "CONFIRMED"
    finance_app.switch_page("pages/lab.py").run()
    assert not finance_app.exception
    assert any("Confirmed ·" in trace.name for chart in finance_app.get("plotly_chart")
               for trace in chart.proto.figure.data)
