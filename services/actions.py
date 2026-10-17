"""Authorized action entry points used by UI routes and future workflow services."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.audit import log_event
from core.lab import LabAssumptions
from core.lab import run_lab as _run_lab
from core.loaders import SyntheticCase
from services.auth import AuthenticatedUser
from services.permissions import authorize


def record_upload(user: AuthenticatedUser | None, filename: str, row_count: int, *, db_path: str | Path | None = None) -> int:
    actor = authorize(user, "data.upload", db_path=str(db_path) if db_path else None)
    return log_event(actor.username, actor.role, "upload.validated", "data_upload",
                     {"filename": Path(filename).name, "row_count": max(0, int(row_count))}, db_path=db_path)


def record_scenario_change(user: AuthenticatedUser | None, case_name: str, changed_fields: list[str], *,
                           db_path: str | Path | None = None) -> int:
    actor = authorize(user, "scenario.change", db_path=str(db_path) if db_path else None)
    return log_event(actor.username, actor.role, "scenario.changed", case_name,
                     {"changed_fields": [str(field)[:80] for field in changed_fields[:50]]}, db_path=db_path)


def run_lab(user: AuthenticatedUser | None, case: SyntheticCase, assumptions: LabAssumptions | None = None,
            *, db_path: str | Path | None = None):
    actor = authorize(user, "lab.run", db_path=str(db_path) if db_path else None)
    result = _run_lab(case, assumptions)
    log_event(actor.username, actor.role, "scenario.run", case.profile.business_id,
              {"plan_count": len(result.plans)}, db_path=db_path)
    return result


def create_action_draft(user: AuthenticatedUser | None, entity: str, summary: dict[str, Any], *,
                        db_path: str | Path | None = None) -> int:
    actor = authorize(user, "draft.create", db_path=str(db_path) if db_path else None)
    return log_event(actor.username, actor.role, "draft.created", entity, summary, db_path=db_path)


def review_action_draft(user: AuthenticatedUser | None, draft_id: str, decision: str, *,
                        db_path: str | Path | None = None) -> int:
    if decision not in {"approve", "reject"}:
        raise ValueError("Decision must be approve or reject.")
    action = "draft.approve" if decision == "approve" else "draft.reject"
    actor = authorize(user, action, db_path=str(db_path) if db_path else None)
    return log_event(actor.username, actor.role, f"draft.{decision}d" if decision == "approve" else "draft.rejected",
                     draft_id, {"decision": decision}, db_path=db_path)


def record_simulated_execution(user: AuthenticatedUser | None, draft_id: str, *,
                               db_path: str | Path | None = None) -> int:
    actor = authorize(user, "execution.simulate", db_path=str(db_path) if db_path else None)
    return log_event(actor.username, actor.role, "execution.simulated", draft_id,
                     {"mode": "simulated; no external action"}, db_path=db_path)


def move_money(user: AuthenticatedUser | None, amount: float, *, db_path: str | Path | None = None) -> None:
    authorize(user, "money.move", db_path=str(db_path) if db_path else None)
    # The registry always denies this action; this line is unreachable by design.

