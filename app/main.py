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


def run() -> None:
    """Render the shell: page config, sidebar, hidden navigation, page body."""
    st.set_page_config(
        layout="wide",
        page_title=ui.TITLE,
        page_icon=ui.PAGES[0][2],
        initial_sidebar_state="expanded",
    )
    ui.load_styles()
    ui.sidebar_top()
    pages = [
        st.Page(path, title=title, icon=icon, default=path == ui.PAGES[0][1])
        for title, path, icon in ui.PAGES
    ]
    pg = st.navigation(pages, position="hidden")
    ui.sidebar_bottom("Not signed in", "viewer")
    pg.run()


if __name__ == "__main__":
    run()
