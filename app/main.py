"""StratifyAI application shell (T02).

Layout per docs/DESIGN.md: page config, sidebar branding, the 10-page
navigation, and a footer on every page. Pages under app/pages/ are stubs that
show the design system; the feature tasks (T03-T18) replace them in place.

Navigation is rendered by hand (components.sidebar_top -> st.page_link) and
st.navigation(position="hidden") only selects which page runs, so the brand,
the menu and the role badge share one layout instead of the built-in nav
inserting itself above our own content.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import components as ui
from services.auth import AuthenticationError, current_user, login, login_demo, logout
from services.permissions import can_user

PAGE_ACTIONS = {
    "pages/lab.py": "lab.run",
    "pages/upload.py": "data.upload",
    "pages/assumptions.py": "assumptions.manage",
    "pages/approvals.py": "approvals.view",
}


def _login_panel() -> None:
    st.title("StratifyAI sign in")
    st.caption("DEMO authentication for the synthetic-data prototype. Use credentials configured in .env or the labelled demo defaults.")
    with st.form("login-form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        try:
            login(username, password)
            st.rerun()
        except AuthenticationError as exc:
            st.error(str(exc))
        except Exception:  # noqa: BLE001 - hide database/provider details from the login screen
            st.error("Sign in could not be completed. Check the local audit service and try again.")
    st.markdown("### Quick sign-in · DEMO")
    st.caption("Choose a synthetic demo role to enter without typing a password. The regular username and password login remains available above.")
    demo_accounts = (
        ("owner", "Owner"),
        ("finance_ops", "Finance Ops"),
        ("viewer", "Viewer"),
        ("auditor", "Auditor"),
    )
    columns = st.columns(4)
    for column, (username, label) in zip(columns, demo_accounts):
        with column:
            if st.button(f"Continue as {label}", key=f"demo-login-{username}", use_container_width=True):
                try:
                    login_demo(username)
                    st.rerun()
                except Exception:  # noqa: BLE001 - keep audit storage details out of the login screen
                    st.error("Demo sign-in could not be completed. Check the local audit service and try again.")


def run() -> None:
    """Render the shell: page config, sidebar, hidden navigation, page body."""
    st.set_page_config(
        layout="wide",
        page_title=ui.TITLE,
        page_icon=ui.PAGES[0][2],
        initial_sidebar_state="expanded",
    )
    user = current_user()
    if user is None:
        ui.load_styles()
        _login_panel()
        return
    visible = [page for page in ui.PAGES if page[1] not in PAGE_ACTIONS or can_user(user, PAGE_ACTIONS[page[1]])]
    pages = [
        st.Page(path, title=title, icon=icon, default=path == ui.PAGES[0][1])
        for title, path, icon in visible
    ]
    page_by_path = {path: page for (_, path, _), page in zip(visible, pages)}
    pg = st.navigation(pages, position="hidden")
    sidebar_pages = [(title, page_by_path[path], icon) for title, path, icon in visible]
    ui.sidebar_top(sidebar_pages)
    ui.sidebar_bottom(user.display_name, user.role)
    ui.global_context_bar(user)
    with st.sidebar:
        if st.button("Log out", key="auth-logout"):
            logout()
            st.rerun()
    try:
        with st.spinner("Loading page…"):
            pg.run()
    except Exception:  # noqa: BLE001 - keep unexpected page or storage details out of the UI
        st.error("This page could not be loaded. Check the selected data or local service status and try again.")
        ui.footer()


if __name__ == "__main__":
    run()
