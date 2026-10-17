"""Backend action registry and role checks; UI role labels are never authority."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.audit import log_event
from services.auth import AuthenticatedUser, principal_identity

Tier = Literal["READ", "DRAFT", "APPROVAL_REQUIRED", "MONEY_MOVEMENT"]
ROLES = ("owner", "finance_ops", "viewer", "auditor")


@dataclass(frozen=True)
class PermissionRule:
    tier: Tier
    allowed_roles: tuple[str, ...]
    description: str


ACTION_REGISTRY: dict[str, PermissionRule] = {
    "dashboard.view": PermissionRule("READ", ROLES, "View dashboards and computed results"),
    "security.view": PermissionRule("READ", ROLES, "View security controls and system status"),
    "copilot.ask": PermissionRule("READ", ROLES, "Ask read-only questions about computed data"),
    "audit.view": PermissionRule("READ", ("owner", "auditor"), "View and verify audit events"),
    "approvals.view": PermissionRule("READ", ("owner", "auditor"), "View the approval queue and audit log"),
    "lab.run": PermissionRule("DRAFT", ("owner", "finance_ops"), "Run or change a hypothetical scenario"),
    "scenario.change": PermissionRule("DRAFT", ("owner", "finance_ops"), "Save a changed hypothetical scenario"),
    "data.upload": PermissionRule("DRAFT", ("owner", "finance_ops"), "Upload and validate a data file"),
    "draft.create": PermissionRule("DRAFT", ("owner", "finance_ops"), "Create an action draft"),
    "assumptions.manage": PermissionRule("DRAFT", ("owner",), "Edit shared assumptions"),
    "draft.approve": PermissionRule("APPROVAL_REQUIRED", ("owner",), "Approve an action draft"),
    "draft.reject": PermissionRule("APPROVAL_REQUIRED", ("owner",), "Reject an action draft"),
    "execution.simulate": PermissionRule("APPROVAL_REQUIRED", ("owner",), "Record a simulated execution"),
    "money.move": PermissionRule("MONEY_MOVEMENT", (), "Move or transmit money (always denied)"),
}


class PermissionDenied(Exception):
    """A safe authorization failure intended for display to the current user."""


def authorize(
    user: AuthenticatedUser | None,
    action: str,
    *,
    db_path: str | None = None,
) -> AuthenticatedUser:
    identity = principal_identity(user)
    rule = ACTION_REGISTRY.get(action)
    if identity is None or rule is None or identity[1] not in rule.allowed_roles or rule.tier == "MONEY_MOVEMENT":
        actor, role = identity if identity else ("anonymous", "anonymous")
        log_event(actor, role, "authorization.denied", action or "unknown", {"requested_action": action}, db_path=db_path)
        raise PermissionDenied("You are not allowed to perform this action.")
    # Construct a trusted value using role and username resolved from the issued token.
    return AuthenticatedUser(identity[0], identity[0].replace("_", " ").title(), identity[1], user._session_token)


def can_user(user: AuthenticatedUser | None, action: str) -> bool:
    identity = principal_identity(user)
    rule = ACTION_REGISTRY.get(action)
    return bool(identity and rule and identity[1] in rule.allowed_roles and rule.tier != "MONEY_MOVEMENT")


def permission_matrix() -> list[dict[str, str]]:
    return [{"Action": action, "Tier": rule.tier, "Allowed roles": ", ".join(rule.allowed_roles) or "None",
             "Description": rule.description} for action, rule in ACTION_REGISTRY.items()]
