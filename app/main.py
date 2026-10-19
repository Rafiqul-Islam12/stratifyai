"""StratifyAI application shell.

Layout (docs/UI_REDESIGN.md): a fixed top navbar on every screen, a fixed grouped
sidebar, a compact page header, then the page body. Signed-out visitors can read
the public Overview and reach the sign-in screen; no gated page code runs for
them. Signed-in users get the hidden ``st.navigation`` (it only selects which
page runs) plus our own sidebar links.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import components as ui
from app import landing
from services.auth import current_user
from services.permissions import can_user

PAGE_ACTIONS = ui.PAGE_ACTIONS


def _run_signed_out() -> None:
    view = st.session_state.get("sa_view", "home")
    ui.navbar(None, view=view)
    ui.sidebar_signed_out(view)
    if view == "login":
        landing.render_login()
    else:
        landing.render_home()


def _run_signed_in(user) -> None:
    visible_pages = [page for page in ui.PAGES if page[1] not in PAGE_ACTIONS or can_user(user, PAGE_ACTIONS[page[1]])]
    home_page = st.Page(landing.render_home, title="Home", url_path="home", icon=":material/home:")
    workspace_pages = [
        st.Page(path, title=title, icon=icon, default=path == ui.PAGES[0][1])
        for title, path, icon in visible_pages
    ]
    pages = [home_page, *workspace_pages]
    page_by_path = {path: page for (_, path, _), page in zip(visible_pages, workspace_pages)}
    visible = set(page_by_path)
    pg = st.navigation(pages, position="hidden")
    current_path = next((path for title, path, _ in ui.PAGES if title == pg.title), None)
    st.session_state["sa_view"] = "home"
    ui.navbar(user)
    ui.sidebar_signed_in(user, page_by_path, visible, home_page, current_path)

    target = st.session_state.pop("post_login_target", None)
    if target:
        if target in visible and target != ui.PAGES[0][1]:
            st.switch_page(page_by_path[target])
        elif target not in visible and target in PAGE_ACTIONS:
            st.session_state["sa_access_notice"] = (
                f"{ui.PAGE_BY_PATH[target][0]} is not available for the {user.role} role."
            )

    if current_path:
        ui.shell_header(current_path)
    notice = st.session_state.pop("sa_access_notice", None)
    if notice:
        ui.alert_banner("warning", "Page not available for this role", notice)
    try:
        with st.spinner("Loading page…"):
            pg.run()
    except Exception:  # noqa: BLE001 - keep unexpected page or storage details out of the UI
        st.error("This page could not be loaded. Check the selected data or local service status and try again.")
        ui.footer()


def run() -> None:
    """Render the shell: page config, styles, navbar, sidebar, then the signed-out view or the page."""
    st.set_page_config(
        layout="wide",
        page_title=ui.TITLE,
        page_icon="📈",
        initial_sidebar_state="expanded",
    )
    ui.load_styles()
    st.session_state["_sa_shell"] = True
    user = current_user()
    if user is None:
        _run_signed_out()
    else:
        _run_signed_in(user)


if __name__ == "__main__":
    run()
