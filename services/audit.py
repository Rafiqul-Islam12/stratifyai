"""Permission-checked access to audit events and integrity verification."""
from __future__ import annotations

from pathlib import Path

from core.audit import ChainVerification, list_events, log_event
from core.audit import verify_chain as _verify_chain
from services.auth import AuthenticatedUser
from services.permissions import authorize


def get_audit_events(user: AuthenticatedUser | None, *, actor: str | None = None,
                     action: str | None = None, limit: int = 500,
                     db_path: str | Path | None = None) -> list[dict]:
    authorize(user, "audit.view", db_path=str(db_path) if db_path else None)
    return list_events(actor=actor, action=action, limit=limit, db_path=db_path)


def verify_audit_chain(user: AuthenticatedUser | None, *, db_path: str | Path | None = None) -> ChainVerification:
    trusted = authorize(user, "audit.view", db_path=str(db_path) if db_path else None)
    log_event(trusted.username, trusted.role, "audit.verified", "audit_log", db_path=db_path)
    return _verify_chain(db_path=db_path)
