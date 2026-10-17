"""Demo-only PBKDF2 authentication with server-side role resolution."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from pathlib import Path

from core.audit import log_event

PBKDF2_ITERATIONS = 240_000
AUTH_SESSION_KEY = "stratify_auth_token"
DEMO_PASSWORD_DEFAULTS = {
    "owner": "DEMO-owner-123",
    "finance_ops": "DEMO-finance-123",
    "viewer": "DEMO-viewer-123",
    "auditor": "DEMO-auditor-123",
}
ROLES = {"owner": "owner", "finance_ops": "finance_ops", "viewer": "viewer", "auditor": "auditor"}


@dataclass(frozen=True)
class AuthenticatedUser:
    username: str
    display_name: str
    role: str
    _session_token: str = field(repr=False, compare=False)


@dataclass(frozen=True)
class UserRecord:
    username: str
    display_name: str
    role: str
    salt: bytes = field(repr=False)
    password_hash: bytes = field(repr=False)


class AuthenticationError(Exception):
    """Friendly, non-sensitive login failure."""


class InvalidSession(Exception):
    """The session token is absent, expired, revoked or not issued here."""


def _env_file_values() -> dict[str, str]:
    """Read only simple key/value settings from the ignored local .env file."""
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


_LOCAL_ENV = _env_file_values()
_RECORDS: dict[str, UserRecord] = {}
for _username, _role in ROLES.items():
    _password = os.getenv(f"DEMO_{_username.upper()}_PASSWORD") or _LOCAL_ENV.get(f"DEMO_{_username.upper()}_PASSWORD") or DEMO_PASSWORD_DEFAULTS[_username]
    _salt = secrets.token_bytes(16)
    _digest = hashlib.pbkdf2_hmac("sha256", _password.encode("utf-8"), _salt, PBKDF2_ITERATIONS)
    _RECORDS[_username] = UserRecord(_username, _username.replace("_", " ").title(), _role, _salt, _digest)
del _password, _salt, _digest, _username, _role
_ACTIVE_SESSIONS: dict[str, str] = {}


def _state(session_state: MutableMapping | None = None) -> MutableMapping:
    if session_state is not None:
        return session_state
    import streamlit as st
    return st.session_state


def login(
    username: str,
    password: str,
    *,
    session_state: MutableMapping | None = None,
    db_path: str | Path | None = None,
) -> AuthenticatedUser:
    normalized = username.strip().lower() if isinstance(username, str) else ""
    password = password if isinstance(password, str) else ""
    record = _RECORDS.get(normalized)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), record.salt if record else b"\0" * 16, PBKDF2_ITERATIONS)
    valid = record is not None and hmac.compare_digest(candidate, record.password_hash)
    if not valid:
        log_event(normalized or "anonymous", "anonymous", "login.denied", "authentication",
                  {"username": normalized}, db_path=db_path)
        raise AuthenticationError("Username or password is incorrect.")
    token = secrets.token_urlsafe(32)
    _ACTIVE_SESSIONS[token] = record.username
    principal = AuthenticatedUser(record.username, record.display_name, record.role, token)
    _state(session_state)[AUTH_SESSION_KEY] = token
    log_event(record.username, record.role, "login.success", "authentication", db_path=db_path)
    return principal


def current_user(session_state: MutableMapping | None = None) -> AuthenticatedUser | None:
    token = _state(session_state).get(AUTH_SESSION_KEY)
    username = _ACTIVE_SESSIONS.get(token)
    record = _RECORDS.get(username) if username else None
    return AuthenticatedUser(record.username, record.display_name, record.role, token) if record else None


def principal_identity(user: AuthenticatedUser | None) -> tuple[str, str] | None:
    """Resolve identity from the server-issued token; ignore caller-supplied role fields."""
    if not isinstance(user, AuthenticatedUser):
        return None
    username = _ACTIVE_SESSIONS.get(user._session_token)
    record = _RECORDS.get(username) if username else None
    return (record.username, record.role) if record else None


def logout(*, session_state: MutableMapping | None = None, db_path: str | Path | None = None) -> None:
    state = _state(session_state)
    token = state.pop(AUTH_SESSION_KEY, None)
    username = _ACTIVE_SESSIONS.pop(token, None)
    record = _RECORDS.get(username) if username else None
    if record:
        log_event(record.username, record.role, "logout", "authentication", db_path=db_path)


def demo_usernames() -> tuple[str, ...]:
    return tuple(_RECORDS)
