"""Reusable UI primitives for every StratifyAI page (T02).

Implements the component list in docs/DESIGN.md: page_header, kpi_row,
kpi_card, metric_tile, alert_banner, section_title, plan_row, plan_card,
badge, empty_state, info_tooltip, layer_legend, footer - plus sidebar
branding, the sidebar navigation and a shared page stub.

Every component emits its HTML in ONE st.markdown call: Streamlit renders each
call into its own container, so a div opened in one call can never wrap the
content of the next. Colour only comes from app/styles.css (injected by
load_styles) or the chart tokens in app/charts.py, so no page hard-codes one.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import streamlit as st

from app import charts
from app.version import __version__

TITLE = "StratifyAI"
TAGLINE = "The Liquidity Decision Lab for SME Financial Intelligence"

# The 10 pages, defined once: (title, path, icon). The shell builds st.Page and
# the sidebar builds st.page_link from this same list, so the order and the
# labels can never drift apart.
PAGES: list[tuple[str, str, str]] = [
    ("Overview", "pages/overview.py", "🏠"),
    ("Cash Flow", "pages/cashflow.py", "📈"),
    ("Decision Lab", "pages/lab.py", "⚖"),
    ("Financing", "pages/financing.py", "💳"),
    ("Analysis", "pages/analysis.py", "🔍"),
    ("Copilot", "pages/copilot.py", "🤖"),
    ("Approvals", "pages/approvals.py", "✅"),
    ("Data Upload", "pages/upload.py", "📥"),
    ("Assumptions", "pages/assumptions.py", "⚙"),
    ("Security", "pages/security.py", "🔒"),
]
_VERSION = __version__
_STYLES = Path(__file__).with_name("styles.css")

_ALERT_ICONS = {"info": "ℹ", "warning": "⚠", "critical": "✕"}
_BADGE_TONES = ("muted", "success", "warning", "danger", "info", "actual", "forecast", "hypo", "confirm")

# Legend entries, kept in module order so every page shows the same thing.
# Each entry is (label, colour, dash).
_LEGEND_ENTRIES: list[tuple[str, str, str]] = [
    (layer, style["color"], style["dash"]) for layer, style in charts.LAYER_STYLES.items()
] + [("Reserve", charts.RESERVE_COLOR, "dash")]


def _md(content: str) -> None:
    """Render a raw HTML fragment. Every class must exist in styles.css."""
    st.markdown(content, unsafe_allow_html=True)


def _e(text: str) -> str:
    """Escape dynamic text so uploaded or assumed values cannot inject markup."""
    return html.escape(text, quote=True)


def _ctx(container: Any | None) -> Any:
    """A usable render target.

    ``None``, the ``st`` module itself, and anything without a ``.markdown``
    method would all make ``with container or st:`` fail, so fall back to a
    fresh container. Real containers and columns pass through unchanged.
    """
    if container is None or container is st or not callable(getattr(container, "markdown", None)):
        return st.container()
    return container


def _tip(label: str, tooltip: str) -> str:
    """A label wrapped in a hover tooltip."""
    return '<span class="sa-tip" title="' + _e(tooltip) + '">' + _e(label) + "</span>"


def _badge(text: str, tone: str = "muted") -> str:
    """The badge markup, so cards can embed one inside their own string."""
    if tone not in _BADGE_TONES:
        tone = "muted"
    return '<span class="sa-badge sa-tone-' + tone + '">' + _e(text) + "</span>"


def load_styles() -> None:
    """Inject the design system into the current page.

    Guarded by ``st.session_state``: pages call this themselves, the shell
    already calls it, and each call would otherwise append another <style>.
    """
    if st.session_state.get("_sa_styles"):
        return
    st.session_state["_sa_styles"] = True
    _md("<style>" + _STYLES.read_text(encoding="utf-8") + "</style>")


def wordmark() -> None:
    """Sidebar brand block: gradient wordmark, tagline and the data badge."""
    _md('<div class="sa-wordmark">' + _e(TITLE) + "</div>")
    _md('<div class="sa-tagline">' + _e(TAGLINE) + "</div>")
    _md(_badge("Synthetic data", "warning"))


def sidebar_top() -> None:
    """Sidebar top: brand, then the navigation rendered from PAGES.

    Navigation is emitted with ``st.page_link`` here instead of by
    ``st.navigation`` so the brand, the menu and the role badge keep one
    visual rhythm. The hidden navigation still selects which page runs.

    The links are inside ``with st.sidebar``: ``st.page_link`` only renders as
    a sidebar row when its target is the sidebar, otherwise it lands in the
    main column.
    """
    with st.sidebar:
        wordmark()
        for title, path, icon in PAGES:
            st.page_link(path, label=title, icon=icon)


def sidebar_bottom(user: str = "Not signed in", role: str = "viewer") -> None:
    """Current user and role badge, below the navigation."""
    with st.sidebar:
        _md('<hr class="sa-divider">')
        _md('<div class="sa-side-user">' + _e(user) + "</div>")
        badge("Role: " + role, tone="muted")


def badge(text: str, tone: str = "muted") -> None:
    """A pill badge for a layer or a status."""
    _md(_badge(text, tone))


def info_tooltip(label: str, tooltip: str) -> None:
    """A label with a hover tooltip explaining the formula or its source."""
    _md(_tip(label, tooltip))


def page_header(
    title: str,
    purpose: str,
    *,
    business: str | None = None,
    scenario: str | None = None,
) -> None:
    """Page title and one-line purpose, with business and scenario on the right."""
    meta = ""
    if business:
        meta += '<div class="sa-header-meta">Business: ' + _e(business) + "</div>"
    if scenario:
        meta += '<div class="sa-header-meta">Scenario: ' + _e(scenario) + "</div>"
    _md(
        '<div class="sa-header">'
        '<div class="sa-header-main">'
        '<div class="sa-header-title">' + _e(title) + "</div>"
        '<div class="sa-header-purpose">' + _e(purpose) + "</div>"
        "</div>"
        '<div class="sa-header-side">' + meta + "</div>"
        "</div>"
    )


def _delta_html(delta: str) -> str:
    """A delta line, toned by its leading sign."""
    tone = "up" if delta.startswith("+") else "down" if delta.startswith("-") else "flat"
    return '<div class="sa-card-delta sa-delta-' + tone + '">' + _e(delta) + "</div>"


def kpi_row(items: list[tuple[str, str, str]], *, deltas: dict[str, str] | None = None) -> None:
    """A row of equal-width, equal-height KPI tiles in ONE st.markdown.

    ``items`` are ``(label, value, tooltip)`` triples. An optional ``deltas``
    dict adds a delta line to the tiles it names. One CSS grid is emitted in a
    single call instead of an ``st.columns`` loop: loop columns are separate
    containers and never get equal heights.
    """
    cells = []
    for label, value, tip in items:
        delta = deltas.get(label) if deltas else None
        cells.append(
            '<div class="sa-card sa-kpi">'
            '<div class="sa-kpi-title">' + (_tip(label, tip) if tip else _e(label)) + "</div>"
            '<div class="sa-kpi-value num">' + _e(value) + "</div>"
            + (_delta_html(delta) if delta else "")
            + "</div>"
        )
    _md('<div class="sa-row">' + "".join(cells) + "</div>")


def metric_tile(
    container: Any | None,
    label: str,
    value: str,
    *,
    delta: str | None = None,
    tooltip: str | None = None,
) -> None:
    """A single big KPI: the 36px hero value for one headline number."""
    with _ctx(container):
        _md(
            '<div class="sa-card sa-metric">'
            '<div class="sa-card-title">' + (_tip(label, tooltip) if tooltip else _e(label)) + "</div>"
            '<div class="sa-card-value num">' + _e(value) + "</div>" + _delta_html(delta or "") + "</div>"
        )


def kpi_card(
    container: Any | None,
    label: str,
    value: str,
    *,
    delta: str | None = None,
    tooltip: str | None = None,
) -> None:
    """A bordered KPI card with label, value, optional delta and tooltip."""
    with _ctx(container):
        _md(
            '<div class="sa-card">'
            '<div class="sa-card-title">' + (_tip(label, tooltip) if tooltip else _e(label)) + "</div>"
            '<div class="sa-card-value num">' + _e(value) + "</div>" + _delta_html(delta or "") + "</div>"
        )


def alert_banner(tone: str, title: str, body: str, container: Any | None = None) -> None:
    """An info, warning or critical banner."""
    if tone not in _ALERT_ICONS:
        tone = "info"
    with _ctx(container):
        _md(
            '<div class="sa-alert sa-alert-' + tone + '">'
            '<div class="sa-alert-title">' + _ALERT_ICONS[tone] + " " + _e(title) + "</div>"
            '<div class="sa-alert-body">' + _e(body) + "</div></div>"
        )


def section_title(text: str) -> None:
    """A section heading with a divider."""
    _md('<div class="sa-section">' + _e(text) + "</div>")


def _plan_rows_html(rows: list[tuple[str, str]] | None) -> str:
    """The label/value lines inside a plan card."""
    return "".join(
        '<div class="sa-plan-row"><span>' + _e(label) + "</span><span>" + _e(value) + "</span></div>"
        for label, value in rows or []
    )


def plan_row(
    plans: list[tuple[str, list[tuple[str, str]], bool]],
    *,
    cols: int | None = None,
) -> None:
    """A row of equal-width, equal-height plan cards in ONE st.markdown.

    ``plans`` are ``(name, rows, recommended)`` triples and ``rows`` is a list
    of ``(label, value)`` pairs. ``cols`` pins the column count; otherwise the
    number of plans decides it, which lets two rows share one grid template.
    """
    if not plans:
        return
    columns = (cols or len(plans)) or 1
    grid = "grid-template-columns:repeat(" + str(columns) + ",minmax(0,1fr));"
    cells = []
    for name, rows, recommended in plans:
        css = "sa-card sa-plan" + (" sa-plan--recommended" if recommended else "")
        name_html = _e(name)
        if recommended:
            name_html = (
                '<div class="sa-plan-head">' + name_html + _badge("Recommended", "success") + "</div>"
            )
        cells.append(
            '<div class="' + css + '"><div class="sa-plan-name">' + name_html + "</div>"
            + _plan_rows_html(rows) + "</div>"
        )
    _md('<div class="sa-row" style="' + grid + '">' + "".join(cells) + "</div>")


def plan_card(
    container: Any | None,
    name: str,
    rows: list[tuple[str, str]] | None = None,
    *,
    recommended: bool = False,
) -> None:
    """A card for one Liquidity Decision Lab plan."""
    css = "sa-card sa-plan" + (" sa-plan--recommended" if recommended else "")
    name_html = _e(name)
    if recommended:
        name_html = '<div class="sa-plan-head">' + name_html + _badge("Recommended", "success") + "</div>"
    with _ctx(container):
        _md(
            '<div class="' + css + '"><div class="sa-plan-name">' + name_html + "</div>"
            + _plan_rows_html(rows) + "</div>"
        )


def empty_state(caption: str, body: str, call_to_action: str, *, disabled: bool = False) -> None:
    """A dashed empty state with a call to action."""
    _md(
        '<div class="sa-empty">'
        '<div class="sa-empty-title">' + _e(caption) + "</div>"
        '<div class="sa-empty-body">' + _e(body) + "</div></div>"
    )
    st.button(call_to_action, disabled=disabled)


def layer_legend() -> None:
    """The four layers plus the reserve line, in the shared colours."""
    items = "".join(
        '<span class="sa-legend-item">'
        '<span class="sa-swatch" style="border-color:'
        + colour
        + ";border-style:"
        + dash
        + '"></span>'
        '<span class="sa-legend-label">'
        + _e(label)
        + "</span></span>"
        for label, colour, dash in _LEGEND_ENTRIES
    )
    _md('<div class="sa-legend">' + items + "</div>")


def footer(version: str | None = None) -> None:
    """Page footer with version and the required disclaimers."""
    _md(
        '<div class="sa-footer">'
        + _e(TITLE)
        + " | Synthetic data, not financial advice | Illustrative financing terms | v"
        + _e(version or _VERSION)
        + "</div>"
    )


def page_stub(
    *,
    title: str,
    purpose: str,
    kpis: list[tuple[str, str, str]],
    figure: Any,
    note: str,
    call_to_action: str = "Load demo business",
) -> None:
    """A placeholder page: header, KPI row, one labelled chart and a footer."""
    load_styles()
    page_header(title, purpose, business="Demo business")
    kpi_row(list(kpis))
    st.caption("Sample data for layout review only - not computed values.")
    st.plotly_chart(figure, use_container_width=True)
    layer_legend()
    section_title(title)
    empty_state(title + " content lands with its task", note, call_to_action, disabled=True)
    footer()
