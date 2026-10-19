"""Reusable UI primitives for every StratifyAI page.

The design system lives in app/styles.css (tokens, layout, widget restyling) and
app/charts.py (chart theme). This module renders the pieces that need Python:
the fixed top navbar, the fixed grouped sidebar, the compact page header, cards,
KPI grids, plan cards, hero number card, banners, legends, empty/locked states.

Every raw-HTML component emits its markup in ONE st.markdown call and starts
with a block-level tag on a single line (no blank lines, no indentation), so the
markdown parser never splits or code-blocks it. Colour only comes from CSS
variables or app/charts.py; no page hard-codes one.
"""
from __future__ import annotations

import html
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import streamlit as st

from app import charts
from app.icons import logo_mark, svg
from app.version import __version__
from data.generate_synthetic import CASES
from services.permissions import ACTION_REGISTRY

TITLE = "StratifyAI"
TAGLINE = "The Liquidity Decision Lab for SME Financial Intelligence"

# The 10 pages, defined once: (title, path, material icon). The shell builds st.Page
# and the sidebar builds st.page_link from this list, so order and labels never drift.
PAGES: list[tuple[str, str, str]] = [
    ("Overview", "pages/overview.py", ":material/home:"),
    ("Cash Flow", "pages/cashflow.py", ":material/show_chart:"),
    ("Decision Lab", "pages/lab.py", ":material/balance:"),
    ("Financing", "pages/financing.py", ":material/account_balance:"),
    ("Analysis", "pages/analysis.py", ":material/query_stats:"),
    ("Copilot", "pages/copilot.py", ":material/smart_toy:"),
    ("Approvals", "pages/approvals.py", ":material/task_alt:"),
    ("Data Upload", "pages/upload.py", ":material/upload_file:"),
    ("Assumptions", "pages/assumptions.py", ":material/tune:"),
    ("Security", "pages/security.py", ":material/shield:"),
]
PAGE_BY_PATH = {path: (title, icon) for title, path, icon in PAGES}
PAGE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("", ("pages/overview.py",)),
    ("Decide", ("pages/lab.py", "pages/cashflow.py", "pages/financing.py")),
    ("Understand", ("pages/analysis.py", "pages/copilot.py")),
    ("Govern", ("pages/approvals.py", "pages/security.py")),
    ("Data", ("pages/upload.py", "pages/assumptions.py")),
)
# page path -> (one-line purpose, shows the Business/Scenario selectors)
PAGE_META: dict[str, tuple[str, bool]] = {
    "pages/overview.py": ("Business health, cash forecast and the recommended plan in one view.", True),
    "pages/cashflow.py": ("Weekly actuals, a deterministic cash forecast and the first reserve breach.", True),
    "pages/lab.py": ("Compare baseline cash, operational levers, stress tests and illustrative financing.", True),
    "pages/financing.py": ("Compare illustrative funding costs, repayment capacity and readiness.", True),
    "pages/analysis.py": ("Recorded income, expenses, working capital and explainable risk indicators.", True),
    "pages/copilot.py": ("Ask about the computed forecast, plans and readiness evidence.", True),
    "pages/approvals.py": ("Create action drafts, review proposals and verify the audit trail.", False),
    "pages/upload.py": ("Validate transaction, invoice and bill files before using their rows.", False),
    "pages/assumptions.py": ("Edit the values shared by forecasts, Lab levers and illustrative financing.", True),
    "pages/security.py": ("Permission registry, audit status and system controls.", False),
}
# Pages whose access is limited by a backend action (the backend stays authoritative).
PAGE_ACTIONS = {
    "pages/lab.py": "lab.run",
    "pages/upload.py": "data.upload",
    "pages/assumptions.py": "assumptions.manage",
    "pages/approvals.py": "approvals.view",
}
ROLE_INFO: dict[str, tuple[str, str, str]] = {
    "owner": ("Owner", "user", "Makes the final decisions: approves plans and drafts, edits shared assumptions and reviews the audit trail."),
    "finance_ops": ("Finance Ops", "wallet", "Runs the numbers: loads data, tests plans in the Decision Lab and drafts actions for owner approval."),
    "viewer": ("Viewer", "eye", "Follows the business: reads dashboards, forecasts and analysis, and asks the Copilot questions."),
    "auditor": ("Auditor", "search", "Checks the record: verifies the hash-chained audit log and the approval status, read-only."),
}
CASE_LABELS = {
    "stable_healthy": "Stable and healthy", "delayed_customer_payments": "Delayed customer payments",
    "high_expense_shortage": "High expense, shortage", "import_financing": "Import financing",
    "sales_drop_cost_rise": "Sales drop, cost rise",
}
SCENARIO_OPTIONS = ("Forecast baseline", "Option 0", "Option A", "Option B", "Option C")
_CASE_WIDGET_KEYS = (
    "overview-case-select", "cashflow-case-select", "lab-case-select", "financing-case-select",
    "analysis-case-select", "copilot-case-select", "assumptions-case-select", "upload-demo-case-select",
)
_VERSION = __version__
_STYLES = Path(__file__).with_name("styles.css")

_ALERT_ICONS = {"info": "info", "success": "check", "warning": "alert", "critical": "alert"}
_BADGE_TONES = ("muted", "success", "warning", "danger", "info", "actual", "forecast", "hypo", "confirm")
_LEGEND_ENTRIES: list[tuple[str, str, str]] = [
    (layer, style["color"], "dashed" if style["dash"] in ("dash", "dashdot") else "solid")
    for layer, style in charts.LAYER_STYLES.items()
] + [("Reserve", charts.RESERVE_COLOR, "dashed")]


# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------
def _md(content: str) -> None:
    """Render a raw HTML fragment. Every class must exist in styles.css."""
    st.markdown(content, unsafe_allow_html=True)


def _e(text: Any) -> str:
    """Escape dynamic text so uploaded or assumed values cannot inject markup."""
    return html.escape(str(text), quote=True)


def _ctx(container: Any | None) -> Any:
    """A usable render target (falls back to a fresh container)."""
    if container is None or container is st or not callable(getattr(container, "markdown", None)):
        return st.container()
    return container


def _tip(label: str, tooltip: str) -> str:
    return '<span class="sa-tip" title="' + _e(tooltip) + '">' + _e(label) + "</span>"


def _badge(text: str, tone: str = "muted") -> str:
    if tone not in _BADGE_TONES:
        tone = "muted"
    return '<span class="sa-badge sa-tone-' + tone + '">' + _e(text) + "</span>"


def load_styles() -> None:
    """Inject the design system for this Streamlit run (re-injected on every rerun)."""
    _md("<style>" + _STYLES.read_text(encoding="utf-8") + "</style>")


def badge(text: str, tone: str = "muted") -> None:
    _md(_badge(text, tone))


def info_tooltip(label: str, tooltip: str) -> None:
    _md(_tip(label, tooltip))


def icon(name: str, size: int = 20) -> str:
    """Inline SVG icon markup for custom HTML."""
    return svg(name, size)


# ---------------------------------------------------------------------------
# session helpers
# ---------------------------------------------------------------------------
def _sync_business_selection() -> None:
    selected = st.session_state.get("global-business-selector")
    st.session_state["active_synthetic_case"] = selected
    if selected not in CASES:
        return
    for key in _CASE_WIDGET_KEYS:
        if key in st.session_state:
            st.session_state[key] = selected


def active_case(widget_key: str | None = None, *, default_case: str = CASES[0]) -> str:
    """The active case; standalone pages can choose a scenario-appropriate default."""
    active = st.session_state.get("active_synthetic_case")
    fallback = default_case if default_case in CASES else CASES[0]
    if st.session_state.get("_sa_shell") or widget_key is None:
        return active if active in CASES else fallback
    index = CASES.index(active) if active in CASES else CASES.index(fallback)
    return st.selectbox("Synthetic demo case", options=CASES, index=index,
                        format_func=lambda value: CASE_LABELS[value], key=widget_key)

def goto_login(target: str | None = None, notice: str | None = None) -> None:
    """Send a signed-out visitor to the sign-in screen and remember where they were headed."""
    st.session_state["sa_view"] = "login"
    st.session_state["post_login_target"] = target
    st.session_state["login_notice"] = notice
    st.rerun()


def role_can(role: str, action: str) -> bool:
    """Static role check against the backend registry (used for explanatory UI only)."""
    rule = ACTION_REGISTRY.get(action)
    return bool(rule) and rule.tier != "MONEY_MOVEMENT" and role in rule.allowed_roles


def role_pages(role: str) -> list[str]:
    return [title for title, path, _ in PAGES if path not in PAGE_ACTIONS or role_can(role, PAGE_ACTIONS[path])]


# ---------------------------------------------------------------------------
# shell: navbar, sidebar, page header
# ---------------------------------------------------------------------------
def navbar(user: Any | None, *, view: str = "home") -> None:
    """Fixed top navbar built from ONE HTML row (brand, links, badges) plus one Streamlit button pinned to the right.

    No st.columns: the button's element container is positioned by CSS (.st-key-sa-nav-signin / .st-key-auth-logout),
    so the bar cannot reflow when the view changes.
    """
    base = "#" if view == "home" else "/#"  # on the sign-in screen a link returns to the Overview section
    if user is None:
        links = (
            '<nav class="sa-nav-links"><a href="' + base + 'sa-features">Features</a><a href="' + base
            + 'sa-how">How it works</a><a href="' + base + 'sa-roles">Roles</a></nav>'
        )
        right = _badge("Synthetic data", "warning")
    else:
        links = '<nav class="sa-nav-links"></nav>'
        right = _badge("Synthetic data", "warning") + (
            '<span class="sa-badge sa-chip-glass">' + _e(user.display_name) + " · " + _e(user.role) + "</span>"
        )
    with st.container(key="sa-navbar"):
        _md(
            '<div class="sa-navbar-row"><div class="sa-brand">' + logo_mark(38) + '<div><div class="sa-brand-name">' + _e(TITLE)
            + '</div><div class="sa-brand-sub">' + _e(TAGLINE) + "</div></div></div>" + links
            + '<div class="sa-nav-right">' + right + "</div></div>"
        )
        if user is None:
            if view != "login" and st.button("Sign in", key="sa-nav-signin"):
                goto_login()
        elif st.button("Log out", key="auth-logout"):
            from services.auth import logout

            logout()
            st.session_state["sa_view"] = "home"
            st.rerun()


def _guest_card() -> str:
    return (
        '<div class="sa-user"><div class="sa-avatar">?</div><div><div class="sa-user-name">Guest</div>'
        '<div class="sa-user-role">Not signed in</div></div></div>'
    )


def sidebar_signed_in(
    user: Any, page_by_path: dict[str, Any], visible: set[str], home_page: Any, current_path: str | None
) -> None:
    """Fixed sidebar. Same list, same row size as the signed-out sidebar; locked rows only where the role lacks access."""
    with st.sidebar:
        home_key = "side-home-active" if current_path is None else "side-home-inactive"
        if st.button("Home", key=home_key, icon=":material/home:", use_container_width=True):
            st.switch_page(home_page)
        overview_path = PAGES[0][1]
        overview_active = overview_path == current_path
        if overview_path in visible and st.button(
            "Overview",
            key=f"nav-page-{'active' if overview_active else 'inactive'}-overview",
            icon=":material/dashboard:",
            use_container_width=True,
        ):
            st.switch_page(page_by_path[overview_path])
        for title, path, ic in PAGES:
            # Dashboard is the sidebar label for Overview; Home keeps its own overview button.
            if path == overview_path:
                continue
            if path in visible:
                slug = path.split("/")[-1][:-3]
                active = path == current_path
                if st.button(title, key=f"nav-page-{'active' if active else 'inactive'}-{slug}", icon=ic,
                             use_container_width=True):
                    st.switch_page(page_by_path[path])
            else:
                roles = ", ".join(ACTION_REGISTRY[PAGE_ACTIONS[path]].allowed_roles)
                st.button(title, key=f"lock-{path.split('/')[-1][:-3]}", icon=ic, disabled=True,
                          help=f"Available to: {roles}", use_container_width=True)
        initial = (user.display_name or "?")[:1].upper()
        _md(
            '<div class="sa-user"><div class="sa-avatar">' + _e(initial) + '</div><div><div class="sa-user-name">'
            + _e(user.display_name) + '</div><div class="sa-user-role">Role: ' + _e(user.role) + "</div></div></div>"
        )


def sidebar_signed_out(view: str) -> None:
    """Signed-out sidebar: identical list and row size; every workspace page shows a lock and leads to sign-in."""
    with st.sidebar:
        home_key = "side-home-active" if view == "home" else "side-home-inactive"
        if st.button("Home", key=home_key, icon=":material/home:", use_container_width=True):
            st.session_state["sa_view"] = "home"
            st.rerun()
        for title, path, ic in PAGES:
            if path == PAGES[0][1]:
                continue
            if st.button(title, key=f"lock-{path.split('/')[-1][:-3]}", icon=ic, use_container_width=True,
                           help="Sign in to open this page"):
                goto_login(path, f"Sign in to open {title}.")
        _md(_guest_card())


def shell_header(path: str) -> None:
    """Compact page header with the one Business/Scenario selector pair (data pages only)."""
    purpose, show_context = PAGE_META.get(path, ("", False))
    title = PAGE_BY_PATH.get(path, (TITLE, ""))[0]
    text = (
        '<div class="sa-header"><div class="sa-header-main"><div class="sa-crumb">' + _e(TITLE)
        + '</div><div class="sa-header-title">' + _e(title) + '</div><div class="sa-header-purpose">'
        + _e(purpose) + "</div></div></div>"
    )
    if not show_context:
        _md(text)
        return
    active = st.session_state.get("active_synthetic_case")
    if active in CASES and st.session_state.get("global-business-selector") != active:
        st.session_state["global-business-selector"] = active
    elif active not in CASES and st.session_state.get("global-business-selector") is not None:
        st.session_state["global-business-selector"] = None
    st.session_state.setdefault("active_synthetic_case", None)
    if st.session_state.get("global-scenario-selector") not in SCENARIO_OPTIONS:
        st.session_state["global-scenario-selector"] = SCENARIO_OPTIONS[0]
    main, business, scenario = st.columns([5, 3, 2.4], vertical_alignment="bottom")
    with main:
        _md(text)
    with business:
        st.selectbox("Business", (None, *CASES), format_func=lambda v: "No data loaded" if v is None else CASE_LABELS[v],
                     key="global-business-selector", on_change=_sync_business_selection,
                     help="Choose one of the labelled synthetic demo businesses.")
    with scenario:
        st.selectbox("Scenario", SCENARIO_OPTIONS, key="global-scenario-selector",
                     help="Choose the forecast baseline or a Decision Lab plan for the Overview comparison.")


def page_header(title: str, purpose: str, *, business: str | None = None, scenario: str | None = None) -> None:
    """Header for a page run on its own (tests). Inside the shell the shell draws the header."""
    if st.session_state.get("_sa_shell"):
        return
    meta = " · ".join(part for part in (business, scenario) if part)
    side = '<div class="sa-header-side"><div class="sa-header-meta">' + _e(meta) + "</div></div>" if meta else ""
    _md(
        '<div class="sa-header"><div class="sa-header-main"><div class="sa-crumb">' + _e(TITLE)
        + '</div><div class="sa-header-title">' + _e(title) + '</div><div class="sa-header-purpose">'
        + _e(purpose) + "</div></div>" + side + "</div>"
    )


def no_data_state(title: str, purpose: str) -> bool:
    """Render the shell empty state when no business is selected."""
    if not st.session_state.get("_sa_shell"):
        return False
    if st.session_state.get("active_synthetic_case") in CASES:
        return False
    page_header(title, purpose, business="No business selected", scenario="No data loaded")
    slug = title.casefold().replace(" ", "-")
    _md(
        '<div class="sa-empty"><div class="sa-empty-title">No data loaded</div><div class="sa-empty-body">'
        "Choose a labelled synthetic business below, or use the Business selector above, to see this page.</div></div>"
    )
    pick, load = st.columns([3, 2], vertical_alignment="bottom")
    chosen = pick.selectbox("Synthetic demo business", CASES, format_func=lambda v: CASE_LABELS[v], key=f"empty-case-{slug}")
    if load.button("Load demo business", key=f"empty-load-{slug}", type="primary", use_container_width=True):
        st.session_state["active_synthetic_case"] = chosen
        st.rerun()
    footer()
    return True

# ---------------------------------------------------------------------------
# cards and grids
# ---------------------------------------------------------------------------
@contextmanager
def card(key: str, title: str | None = None, subtitle: str | None = None, right: str = "") -> Iterator[None]:
    """A real card: a keyed container that can hold charts, tables and widgets."""
    with st.container(key=f"card-{key}"):
        if title:
            _md(
                '<div class="sa-card-head"><div><div class="sa-card-title">' + _e(title) + "</div>"
                + ('<div class="sa-card-sub">' + _e(subtitle) + "</div>" if subtitle else "")
                + "</div>" + right + "</div>"
            )
        yield


def _delta_html(delta: str) -> str:
    tone = "up" if delta.startswith("+") else "down" if delta.startswith("-") else "flat"
    return '<div class="sa-card-delta sa-delta-' + tone + '">' + _e(delta) + "</div>"


def kpi_row(items: list[tuple[str, str, str]], *, deltas: dict[str, str] | None = None) -> None:
    """A responsive grid of equal-height KPI tiles in ONE st.markdown.

    ``items`` are ``(label, value, tooltip)`` triples.
    """
    cells = []
    for label, value, tip in items:
        delta = deltas.get(label) if deltas else None
        cells.append(
            '<div class="sa-card sa-kpi"><div class="sa-card-title sa-kpi-title">' + (_tip(label, tip) if tip else _e(label))
            + '</div><div class="sa-kpi-value num">' + _e(value) + "</div>" + (_delta_html(delta) if delta else "") + "</div>"
        )
    width = 300 if len(items) == 6 else 210  # six tiles read best as 3 x 2
    _md('<div class="sa-row" style="grid-template-columns:repeat(auto-fit,minmax(' + str(width) + 'px,1fr))">' + "".join(cells) + "</div>")


kpi_grid = kpi_row


def metric_tile(container: Any | None, label: str, value: str, *, delta: str | None = None, tooltip: str | None = None) -> None:
    with _ctx(container):
        _md(
            '<div class="sa-card sa-metric"><div class="sa-card-title">' + (_tip(label, tooltip) if tooltip else _e(label))
            + '</div><div class="sa-card-value num">' + _e(value) + "</div>" + _delta_html(delta or "") + "</div>"
        )


def kpi_card(container: Any | None, label: str, value: str, *, delta: str | None = None, tooltip: str | None = None) -> None:
    with _ctx(container):
        _md(
            '<div class="sa-card"><div class="sa-card-title">' + (_tip(label, tooltip) if tooltip else _e(label))
            + '</div><div class="sa-card-value num">' + _e(value) + "</div>" + _delta_html(delta or "") + "</div>"
        )


def hero_card(label: str, value: str, lines: Sequence[str] = (), bars: Sequence[float] | None = None, bars_caption: str = "") -> None:
    """Dark-green hero number card with an optional mini bar chart (highest-value card on a page)."""
    right = ""
    if bars:
        top = max(abs(v) for v in bars) or 1.0
        cells = "".join(
            '<i class="' + ("now" if i == len(bars) - 1 else "") + '" style="height:' + f"{max(6.0, abs(v) / top * 100):.0f}" + '%"></i>'
            for i, v in enumerate(bars)
        )
        right = '<div><div class="sa-hero-bars-cap">' + _e(bars_caption) + '</div><div class="sa-hero-bars">' + cells + "</div></div>"
    body = "".join("<div>" + _e(line) + "</div>" for line in lines)
    _md(
        '<div class="sa-hero-card"><div><div class="lbl">' + _e(label) + '</div><div class="big">' + _e(value)
        + '</div><div class="sub">' + body + "</div></div>" + right + "</div>"
    )


def alert_banner(tone: str, title: str, body: str, container: Any | None = None) -> None:
    """An info, success, warning or critical banner."""
    if tone not in _ALERT_ICONS:
        tone = "info"
    with _ctx(container):
        _md(
            '<div class="sa-alert sa-alert-' + tone + '">' + svg(_ALERT_ICONS[tone], 18) + '<div><div class="sa-alert-title">'
            + _e(title) + '</div><div class="sa-alert-body">' + _e(body) + "</div></div></div>"
        )


def section_title(text: str) -> None:
    _md('<div class="sa-section">' + _e(text) + "</div>")


def _plan_rows_html(rows: list[tuple[str, str]] | None) -> str:
    return "".join('<div class="sa-plan-row"><span>' + _e(a) + "</span><span>" + _e(b) + "</span></div>" for a, b in rows or [])


def plan_row(plans: list[tuple[str, list[tuple[str, str]], bool]], *, cols: int | None = None) -> None:
    """A row of equal-height plan cards in ONE st.markdown."""
    if not plans:
        return
    grid = "grid-template-columns:repeat(auto-fit,minmax(230px,1fr));" if cols is None else (
        "grid-template-columns:repeat(" + str(cols) + ",minmax(0,1fr));")
    cells = []
    for name, rows, recommended in plans:
        css = "sa-card sa-plan" + (" sa-plan--recommended" if recommended else "")
        head = '<div class="sa-plan-head"><div class="sa-plan-name">' + _e(name) + "</div>" + (
            _badge("Recommended", "success") if recommended else "") + "</div>"
        cells.append('<div class="' + css + '">' + head + _plan_rows_html(rows) + "</div>")
    _md('<div class="sa-row" style="' + grid + '">' + "".join(cells) + "</div>")


def plan_card(container: Any | None, name: str, rows: list[tuple[str, str]] | None = None, *, recommended: bool = False) -> None:
    css = "sa-card sa-plan" + (" sa-plan--recommended" if recommended else "")
    head = '<div class="sa-plan-head"><div class="sa-plan-name">' + _e(name) + "</div>" + (
        _badge("Recommended", "success") if recommended else "") + "</div>"
    with _ctx(container):
        _md('<div class="' + css + '">' + head + _plan_rows_html(rows) + "</div>")


def progress_rows(items: Sequence[tuple[str, str, float]]) -> None:
    """Label, value text and a thin bar. ``pct`` is 0-100."""
    rows = "".join(
        '<div class="sa-prog"><div class="sa-prog-top"><span>' + _e(label) + "</span><span>" + _e(text)
        + '</span></div><div class="sa-prog-bar"><i style="width:' + f"{max(0.0, min(100.0, pct)):.1f}" + '%"></i></div></div>'
        for label, text, pct in items
    )
    _md("<div>" + rows + "</div>")


def activity_list(items: Sequence[tuple[str, str, str, str]], empty: str = "Nothing to show yet.") -> None:
    """Icon, title, detail and time per row (pending approvals, latest audit events)."""
    if not items:
        _md('<div class="sa-card-sub">' + _e(empty) + "</div>")
        return
    rows = "".join(
        '<div class="sa-act"><div class="ic">' + svg(ic, 18) + '</div><div><div class="sa-act-title">' + _e(title)
        + '</div><div class="sa-act-detail">' + _e(detail) + '</div></div><div class="sa-act-time">' + _e(when) + "</div></div>"
        for ic, title, detail, when in items
    )
    _md("<div>" + rows + "</div>")


def chips(labels: Sequence[str], tone: str = "muted") -> None:
    _md('<div class="sa-chip-row">' + "".join(_badge(label, tone) for label in labels) + "</div>")


def empty_state(caption: str, body: str, call_to_action: str, *, disabled: bool = False, key: str | None = None) -> bool:
    """A dashed empty state with a call to action."""
    _md(
        '<div class="sa-empty"><div class="sa-empty-title">' + _e(caption) + '</div><div class="sa-empty-body">'
        + _e(body) + "</div></div>"
    )
    return st.button(call_to_action, disabled=disabled, key=key)


def locked_card(title: str, body: str, who: str = "") -> None:
    """Explain that a page or feature needs a different role or a sign-in."""
    _md(
        '<div class="sa-locked"><div class="ic">' + svg("lock", 24) + '</div><div><div class="sa-card-title">' + _e(title)
        + '</div><div class="sa-card-sub">' + _e(body) + (" Available to: " + _e(who) + "." if who else "") + "</div></div></div>"
    )


def layer_legend() -> None:
    """The four layers plus the reserve line, in the shared colours."""
    items = "".join(
        '<span class="sa-legend-item"><span class="sa-swatch" style="border-color:' + colour + ";border-style:" + dash
        + '"></span><span class="sa-legend-label">' + _e(label) + "</span></span>"
        for label, colour, dash in _LEGEND_ENTRIES
    )
    _md('<div class="sa-legend">' + items + "</div>")


def footer(version: str | None = None) -> None:
    """Page footer with version and the required disclaimers."""
    _md(
        '<div class="sa-footer"><span>' + _e(TITLE) + "</span><span>·</span><span>Synthetic data, not financial advice</span>"
        "<span>·</span><span>Illustrative financing terms</span><span>·</span><span>v" + _e(version or _VERSION) + "</span></div>"
    )
