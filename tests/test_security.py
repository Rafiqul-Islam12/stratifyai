"""T11 backend authentication, permissions and append-only audit coverage."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.audit import init_db, list_events, log_event, verify_chain
from services.actions import move_money
from services.auth import (
    DEMO_PASSWORD_DEFAULTS,
    AuthenticationError,
    current_user,
    login,
    logout,
)
from services.permissions import ACTION_REGISTRY, PermissionDenied, authorize, can_user


@pytest.fixture
def audit_db(tmp_path):
    return tmp_path / "audit.sqlite3"


def _login(role: str, audit_db):
    state = {}
    user = login(role, DEMO_PASSWORD_DEFAULTS[role], session_state=state, db_path=audit_db)
    return user, state


def test_role_action_matrix_and_denials_are_logged(audit_db):
    users = {role: _login(role, audit_db)[0] for role in ("owner", "finance_ops", "viewer", "auditor")}
    for action, rule in ACTION_REGISTRY.items():
        for role, user in users.items():
            allowed = role in rule.allowed_roles and rule.tier != "MONEY_MOVEMENT"
            assert can_user(user, action) is allowed, (role, action)
            if allowed:
                assert authorize(user, action).role == role
            else:
                with pytest.raises(PermissionDenied):
                    authorize(user, action, db_path=str(audit_db))

    denials = [row for row in list_events(action="authorization.denied", db_path=audit_db)]
    assert len(denials) == sum(
        1 for rule in ACTION_REGISTRY.values() for role in users
        if role not in rule.allowed_roles or rule.tier == "MONEY_MOVEMENT"
    )


def test_money_movement_denied_for_every_role_including_owner(audit_db):
    for role in ("owner", "finance_ops", "viewer", "auditor"):
        user, _ = _login(role, audit_db)
        with pytest.raises(PermissionDenied):
            move_money(user, 100, db_path=audit_db)
    assert len(list_events(action="authorization.denied", db_path=audit_db)) == 4


def test_password_login_logout_and_server_side_role_resolution(audit_db):
    state = {"username": "owner", "role": "owner"}
    assert current_user(state) is None
    with pytest.raises(AuthenticationError):
        login("owner", "wrong", session_state=state, db_path=audit_db)
    user = login("viewer", DEMO_PASSWORD_DEFAULTS["viewer"], session_state=state, db_path=audit_db)
    state["role"] = "owner"
    forged = replace(user, role="owner", username="owner")
    assert current_user(state).role == "viewer"
    assert authorize(forged, "dashboard.view", db_path=str(audit_db)).role == "viewer"
    with pytest.raises(PermissionDenied):
        authorize(forged, "audit.view", db_path=str(audit_db))
    logout(session_state=state, db_path=audit_db)
    assert current_user(state) is None


def test_audit_chain_sanitizes_and_detects_tampering(audit_db):
    init_db(audit_db)
    log_event("owner", "owner", "draft.created", "sample", {
        "password": "do-not-store", "note": "Bearer abc123", "summary": "A safe draft"
    }, db_path=audit_db)
    assert verify_chain(db_path=audit_db).ok
    payload = json.loads(list_events(db_path=audit_db)[0]["payload_json"])
    assert "password" not in payload
    assert "abc123" not in json.dumps(payload)

    with sqlite3.connect(audit_db) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE audit_log SET entity='tampered' WHERE id=1")
        connection.execute("DROP TRIGGER audit_log_no_update")
        connection.execute("UPDATE audit_log SET entity='tampered' WHERE id=1")
    result = verify_chain(db_path=audit_db)
    assert not result.ok
    assert result.broken_index == 1


def test_login_screen_accepts_a_demo_user(monkeypatch, audit_db):
    monkeypatch.setenv("STRATIFY_AUDIT_DB", str(audit_db))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app" / "main.py", default_timeout=30)
    app.session_state["sa_view"] = "login"  # signed-out visitors land on the public Overview; this opens the sign-in screen
    app.run()
    assert not app.exception
    app.text_input[0].set_value("viewer")
    app.text_input[1].set_value(DEMO_PASSWORD_DEFAULTS["viewer"])
    app.button(key="login-submit").click().run()
    assert not app.exception
    assert any("Viewer" in item.value for item in app.markdown)


@pytest.mark.parametrize("role,label", [
    ("owner", "Owner"),
    ("finance_ops", "Finance Ops"),
    ("viewer", "Viewer"),
    ("auditor", "Auditor"),
])
def test_demo_shortcut_buttons_open_each_role(monkeypatch, audit_db, role, label):
    monkeypatch.setenv("STRATIFY_AUDIT_DB", str(audit_db))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app" / "main.py", default_timeout=30).run()
    demo_button = next(button for button in app.button if button.key == f"demo-login-{role}")
    demo_button.click().run()
    assert not app.exception
    assert any(label in item.value for item in app.markdown)
    if role == "auditor":
        app.switch_page("pages/approvals.py").run()
        assert not app.exception

