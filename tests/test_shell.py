"""Shell tests: public Overview, locked navigation, sign-in redirect and role cards."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from services.permissions import ACTION_REGISTRY, ROLES

MAIN = Path(__file__).resolve().parents[1] / "app" / "main.py"


def _text(app: AppTest) -> str:
    return "\n".join(item.value for item in app.markdown)


def test_signed_out_visitor_sees_the_public_overview(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATIFY_AUDIT_DB", str(tmp_path / "audit.sqlite3"))
    app = AppTest.from_file(MAIN, default_timeout=30).run()
    assert not app.exception
    text = _text(app)
    assert "Know your cash gap before it happens." in text
    assert "The Liquidity Decision Lab for SME Financial Intelligence" in text
    for role in ROLES:
        assert app.button(key=f"demo-login-{role}") is not None


def test_locked_sidebar_item_opens_sign_in_and_remembers_the_target(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATIFY_AUDIT_DB", str(tmp_path / "audit.sqlite3"))
    app = AppTest.from_file(MAIN, default_timeout=30).run()
    app.button(key="lock-lab").click().run()
    assert not app.exception
    assert app.session_state["sa_view"] == "login"
    assert app.session_state["post_login_target"] == "pages/lab.py"
    assert "Sign in to open Decision Lab." in _text(app)


def test_signing_in_as_a_role_without_access_explains_instead_of_failing(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATIFY_AUDIT_DB", str(tmp_path / "audit.sqlite3"))
    app = AppTest.from_file(MAIN, default_timeout=30)
    app.session_state["sa_view"] = "login"
    app.session_state["post_login_target"] = "pages/lab.py"
    app.run()
    app.button(key="demo-login-viewer").click().run()
    assert not app.exception
    assert "not available for the viewer role" in _text(app)


def test_role_cards_are_derived_from_the_backend_registry():
    from app import landing

    non_money = [action for action, rule in ACTION_REGISTRY.items() if rule.tier != "MONEY_MOVEMENT"]
    for role in ROLES:
        can, cannot = landing.role_lists(role)
        assert len(can) + len(cannot) == len(non_money)
    viewer_can, viewer_cannot = landing.role_lists("viewer")
    assert ACTION_REGISTRY["lab.run"].description in viewer_cannot
    assert ACTION_REGISTRY["dashboard.view"].description in viewer_can


def test_streamlit_is_importable_for_the_shell():
    assert importlib.util.find_spec("streamlit") is not None
