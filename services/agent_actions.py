"""Persistent, permission-checked drafts and offline simulated execution."""
from __future__ import annotations

import html
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.audit import log_event
from services.auth import AuthenticatedUser
from services.permissions import PermissionDenied, authorize

ACTION_TYPES = {
    "collection_reminder",
    "supplier_deferral_request",
    "financing_application_pack",
    "plan_proposal",
}
STATUSES = {"draft", "pending_approval", "approved", "rejected", "simulated_executed"}
DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "agent_actions.sqlite3"
DEFAULT_SANDBOX_LOG = Path(__file__).resolve().parents[1] / "evidence" / "sandbox_log.jsonl"


class InvalidTransition(ValueError):
    """Raised when a draft cannot move to the requested state."""


@dataclass(frozen=True)
class Draft:
    draft_id: str
    action_type: str
    status: str
    created_by: str
    created_at: str
    updated_at: str
    payload: dict[str, Any]
    reviewer: str | None
    review_comment: str
    timeline: tuple[dict[str, str], ...]


def _db_path(db_path: str | Path | None) -> Path:
    return Path(db_path or os.getenv("STRATIFY_AGENT_ACTIONS_DB") or DEFAULT_DB)


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = _db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=10000")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _init(db_path: str | Path | None = None) -> None:
    with _connect(db_path) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS agent_drafts (
            draft_id TEXT PRIMARY KEY,
            action_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            reviewer TEXT,
            review_comment TEXT NOT NULL DEFAULT '',
            simulated_at TEXT
        )""")
        connection.execute("""CREATE TABLE IF NOT EXISTS agent_draft_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            detail_json TEXT NOT NULL,
            FOREIGN KEY (draft_id) REFERENCES agent_drafts(draft_id)
        )""")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _text(value: Any, name: str, *, required: bool = True, limit: int = 300) -> str:
    if not isinstance(value, str):
        value = "" if value is None else str(value)
    result = value.strip()[:limit]
    if required and not result:
        raise ValueError(f"{name} is required.")
    return html.escape(result, quote=True)


def _amount(value: Any, name: str = "Amount") -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive number.") from exc
    if not 0 < number <= 1_000_000_000_000:
        raise ValueError(f"{name} must be a positive number.")
    return round(number, 2)


def _build_payload(action_type: str, fields: dict[str, Any]) -> dict[str, Any]:
    if action_type not in ACTION_TYPES:
        raise ValueError("Choose a supported draft action.")
    if action_type == "collection_reminder":
        customer = _text(fields.get("customer"), "Customer")
        invoice = _text(fields.get("invoice"), "Invoice reference")
        amount = _amount(fields.get("amount"))
        due_date = _text(fields.get("due_date"), "Due date", limit=40)
        note = _text(fields.get("note", ""), "Note", required=False)
        message = (f"Draft only — Hello {customer}, invoice {invoice} for BDT {amount:,.2f} was due "
                   f"{due_date}. Please confirm expected payment timing. {note}").strip()
        return {"customer": customer, "invoice": invoice, "amount": amount, "due_date": due_date,
                "note": note, "message_preview": message, "execution_policy": "manual review only"}
    if action_type == "supplier_deferral_request":
        supplier = _text(fields.get("supplier"), "Supplier")
        invoice = _text(fields.get("invoice"), "Invoice reference")
        amount = _amount(fields.get("amount"))
        current_due = _text(fields.get("current_due_date"), "Current due date", limit=40)
        requested_due = _text(fields.get("requested_due_date"), "Requested due date", limit=40)
        note = _text(fields.get("note", ""), "Note", required=False)
        message = (f"Draft only — Hello {supplier}, we request a discussion about moving invoice {invoice} "
                   f"(BDT {amount:,.2f}) from {current_due} to {requested_due}. {note}").strip()
        return {"supplier": supplier, "invoice": invoice, "amount": amount,
                "current_due_date": current_due, "requested_due_date": requested_due,
                "note": note, "message_preview": message, "execution_policy": "manual review only"}
    if action_type == "financing_application_pack":
        amount = _amount(fields.get("amount"))
        purpose = _text(fields.get("purpose"), "Purpose")
        repayment = _text(fields.get("repayment_plan"), "Repayment plan", limit=1000)
        cash_flow = _text(fields.get("cash_flow_summary"), "Cash-flow summary", limit=1000)
        readiness = _text(fields.get("readiness"), "Readiness summary", limit=1000)
        return {"amount": amount, "purpose": purpose, "repayment_plan": repayment,
                "cash_flow_summary": cash_flow, "readiness": readiness,
                "pack_preview": (f"Illustrative financing pack — BDT {amount:,.2f}; purpose: {purpose}; "
                                 f"repayment: {repayment}; cash flow: {cash_flow}; readiness: {readiness}"),
                "execution_policy": "draft only; no application is submitted"}
    if action_type == "plan_proposal":
        case_name = _text(fields.get("case_name"), "Scenario")
        plan_id = _text(fields.get("plan_id"), "Plan")
        snapshot = fields.get("plan_snapshot")
        if not isinstance(snapshot, dict):
            raise ValueError("Plan proposal requires a structured Lab plan snapshot.")
        return {"case_name": case_name, "plan_id": plan_id, "plan_snapshot": snapshot,
                "assumptions_layer": "HYPOTHETICAL",
                "proposal_preview": f"Lab plan {plan_id} for {case_name}; owner review required."}
    raise ValueError("Choose a supported draft action.")


def _append_event(connection: sqlite3.Connection, draft_id: str, actor: str, action: str,
                  detail: dict[str, Any] | None = None) -> None:
    connection.execute("INSERT INTO agent_draft_events (draft_id, ts, actor, action, detail_json) VALUES (?, ?, ?, ?, ?)",
        (draft_id, _now(), actor, action, json.dumps(detail or {}, sort_keys=True, separators=(",", ":"))))


def _load(connection: sqlite3.Connection, row: sqlite3.Row) -> Draft:
    events = connection.execute("SELECT ts, actor, action FROM agent_draft_events WHERE draft_id=? ORDER BY id",
                               (row["draft_id"],)).fetchall()
    return Draft(row["draft_id"], row["action_type"], row["status"], row["created_by"], row["created_at"],
                 row["updated_at"], json.loads(row["payload_json"]), row["reviewer"], row["review_comment"],
                 tuple(dict(event) for event in events))


def create_draft(user: AuthenticatedUser | None, action_type: str, fields: dict[str, Any], *,
                 db_path: str | Path | None = None) -> Draft:
    actor = authorize(user, "draft.create", db_path=str(db_path) if db_path else None)
    payload = _build_payload(action_type, fields)
    draft_id, now = uuid.uuid4().hex, _now()
    _init(db_path)
    with _connect(db_path) as connection:
        connection.execute("""INSERT INTO agent_drafts
            (draft_id, action_type, status, created_by, created_at, updated_at, payload_json)
            VALUES (?, ?, 'draft', ?, ?, ?, ?)""",
            (draft_id, action_type, actor.username, now, now,
             json.dumps(payload, sort_keys=True, separators=(",", ":"))))
        _append_event(connection, draft_id, actor.username, "draft.created")
    log_event(actor.username, actor.role, "draft.created", draft_id,
              {"action_type": action_type}, db_path=db_path)
    return get_draft(user, draft_id, db_path=db_path)


def submit_draft(user: AuthenticatedUser | None, draft_id: str, *,
                 db_path: str | Path | None = None) -> Draft:
    actor = authorize(user, "draft.create", db_path=str(db_path) if db_path else None)
    _init(db_path)
    with _connect(db_path) as connection:
        row = connection.execute("SELECT * FROM agent_drafts WHERE draft_id=?", (draft_id,)).fetchone()
        if row is None:
            raise KeyError("Draft was not found.")
        if row["created_by"] != actor.username:
            raise PermissionDenied("You can only submit drafts you created.")
        if row["status"] == "pending_approval":
            return _load(connection, row)
        if row["status"] != "draft":
            raise InvalidTransition("Only a draft can be submitted for approval.")
        now = _now()
        connection.execute("UPDATE agent_drafts SET status='pending_approval', updated_at=? WHERE draft_id=?",
                           (now, draft_id))
        _append_event(connection, draft_id, actor.username, "submitted")
        row = connection.execute("SELECT * FROM agent_drafts WHERE draft_id=?", (draft_id,)).fetchone()
        result = _load(connection, row)
    log_event(actor.username, actor.role, "draft.submitted", draft_id, db_path=db_path)
    return result


def list_drafts(user: AuthenticatedUser | None, *, status: str | None = None,
                db_path: str | Path | None = None) -> list[Draft]:
    actor = authorize(user, "approvals.view", db_path=str(db_path) if db_path else None)
    if status is not None and status not in STATUSES:
        raise ValueError("Unknown draft status.")
    _init(db_path)
    conditions, params = [], []
    if actor.role == "auditor":
        return []
    if actor.role == "finance_ops":
        conditions.append("created_by=?")
        params.append(actor.username)
    if status:
        conditions.append("status=?")
        params.append(status)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with _connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM agent_drafts {where} ORDER BY created_at DESC", params).fetchall()
        return [_load(connection, row) for row in rows]


def get_draft(user: AuthenticatedUser | None, draft_id: str, *,
              db_path: str | Path | None = None) -> Draft:
    actor = authorize(user, "approvals.view", db_path=str(db_path) if db_path else None)
    _init(db_path)
    with _connect(db_path) as connection:
        row = connection.execute("SELECT * FROM agent_drafts WHERE draft_id=?", (draft_id,)).fetchone()
        if row is None:
            raise KeyError("Draft was not found.")
        if actor.role == "auditor":
            raise PermissionDenied("Auditors can review the audit trail, not draft contents.")
        if actor.role == "finance_ops" and row["created_by"] != actor.username:
            raise PermissionDenied("You can only view drafts you created.")
        return _load(connection, row)


def review_draft(user: AuthenticatedUser | None, draft_id: str, decision: str, comment: str = "", *,
                 db_path: str | Path | None = None) -> Draft:
    if decision not in {"approve", "reject"}:
        raise ValueError("Decision must be approve or reject.")
    actor = authorize(user, f"draft.{decision}", db_path=str(db_path) if db_path else None)
    comment = _text(comment, "Review comment", required=False, limit=1000)
    target = "approved" if decision == "approve" else "rejected"
    _init(db_path)
    with _connect(db_path) as connection:
        row = connection.execute("SELECT * FROM agent_drafts WHERE draft_id=?", (draft_id,)).fetchone()
        if row is None:
            raise KeyError("Draft was not found.")
        if row["status"] == target:
            return _load(connection, row)
        if row["status"] != "pending_approval":
            raise InvalidTransition("Only a pending draft can be approved or rejected.")
        payload = json.loads(row["payload_json"])
        now = _now()
        if decision == "approve" and row["action_type"] == "plan_proposal":
            payload["assumptions_layer"] = "CONFIRMED"
            payload["confirmed_by"] = actor.username
            payload["confirmed_at"] = now
        connection.execute("""UPDATE agent_drafts SET status=?, updated_at=?, payload_json=?, reviewer=?,
            review_comment=? WHERE draft_id=?""",
            (target, now, json.dumps(payload, sort_keys=True, separators=(",", ":")), actor.username, comment, draft_id))
        _append_event(connection, draft_id, actor.username, target, {"comment": comment})
        row = connection.execute("SELECT * FROM agent_drafts WHERE draft_id=?", (draft_id,)).fetchone()
        result = _load(connection, row)
    log_event(actor.username, actor.role, f"draft.{target}", draft_id,
              {"action_type": result.action_type, "comment": comment}, db_path=db_path)
    return result


def simulate_execution(user: AuthenticatedUser | None, draft_id: str, *,
                       db_path: str | Path | None = None,
                       sandbox_log: str | Path | None = None) -> Draft:
    actor = authorize(user, "execution.simulate", db_path=str(db_path) if db_path else None)
    _init(db_path)
    with _connect(db_path) as connection:
        row = connection.execute("SELECT * FROM agent_drafts WHERE draft_id=?", (draft_id,)).fetchone()
        if row is None:
            raise KeyError("Draft was not found.")
        if row["status"] == "simulated_executed":
            return _load(connection, row)
        if row["status"] != "approved":
            raise InvalidTransition("Only an approved draft can be simulated.")
        event = {"draft_id": draft_id, "action_type": row["action_type"], "actor": actor.username,
                 "simulated_at": _now(), "mode": "sandbox_only", "network_sent": False}
        path = Path(sandbox_log or os.getenv("STRATIFY_SANDBOX_LOG") or DEFAULT_SANDBOX_LOG)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing_ids = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    existing_ids.add(json.loads(line).get("draft_id"))
                except (json.JSONDecodeError, AttributeError):
                    continue
        if draft_id not in existing_ids:
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        now = event["simulated_at"]
        connection.execute("UPDATE agent_drafts SET status='simulated_executed', updated_at=?, simulated_at=? WHERE draft_id=?",
                           (now, now, draft_id))
        _append_event(connection, draft_id, actor.username, "simulated_executed", {"network_sent": False})
        row = connection.execute("SELECT * FROM agent_drafts WHERE draft_id=?", (draft_id,)).fetchone()
        result = _load(connection, row)
    log_event(actor.username, actor.role, "execution.simulated", draft_id,
              {"action_type": result.action_type, "network_sent": False}, db_path=db_path)
    return result


def confirmed_plans(user: AuthenticatedUser | None, case_name: str, *,
                    db_path: str | Path | None = None) -> list[dict[str, Any]]:
    authorize(user, "dashboard.view", db_path=str(db_path) if db_path else None)
    _init(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute("""SELECT payload_json FROM agent_drafts
            WHERE action_type='plan_proposal' AND status IN ('approved','simulated_executed')
            ORDER BY updated_at DESC""").fetchall()
    confirmed = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        if payload.get("case_name") == case_name and payload.get("assumptions_layer") == "CONFIRMED":
            confirmed.append(payload)
    return confirmed
