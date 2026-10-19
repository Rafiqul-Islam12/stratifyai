"""Public Overview (signed out), sign-in screen and the shared "how it works" content.

Everything here is explanatory UI. It never computes forecast numbers and never
decides permissions: role cards read the backend registry, and the sign-in screen
calls the same ``login`` / ``login_demo`` services as before.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import streamlit as st

from app import charts
from app import components as ui
from app.components import _e, _md
from app.icons import logo_mark, svg
from services.auth import AuthenticationError, current_user, login, login_demo
from services.permissions import ACTION_REGISTRY, ROLES

# (key, title, one-line promise, icon, page path)
FEATURES: tuple[tuple[str, str, str, str, str], ...] = (
    ("lab", "Liquidity Decision Lab", "Compare four plans for closing a cash gap, with costs and risks.", "flask", "pages/lab.py"),
    ("cash", "Cash-Flow Forecast", "13-week forecast with an uncertainty band and the first shortage week.", "trend", "pages/cashflow.py"),
    ("fin", "Financing Advisor", "Illustrative loan, invoice and supplier-credit costs and readiness.", "bank", "pages/financing.py"),
    ("copilot", "Evidence Copilot", "Plain-language answers, each with an evidence receipt.", "sparkles", "pages/copilot.py"),
    ("appr", "Approvals and Audit", "Owner approval for every action and a tamper-evident log.", "shield", "pages/approvals.py"),
)
QUESTIONS: tuple[tuple[str, str, str, str, str], ...] = (
    ("When will cash run short?", "A weekly forecast shows the first week the balance falls below your reserve, with a probability.", "clock", "Cash Flow", "pages/cashflow.py"),
    ("How much funding do we need?", "The gap is the reserve minus the lowest projected balance, plus an optional buffer.", "wallet", "Cash Flow", "pages/cashflow.py"),
    ("Can we avoid borrowing?", "Collections, supplier deferral and cost cuts are tested before any loan is considered.", "scale", "Decision Lab", "pages/lab.py"),
    ("Which financing options are worth comparing?", "Cost, repayment schedule and capacity for each template, with every assumption shown.", "bank", "Financing", "pages/financing.py"),
    ("What if sales fall or payments are late?", "Stress tests rerun every plan under falling sales, cost rises, delays and FX shocks.", "bars", "Decision Lab", "pages/lab.py"),
)
STEPS: tuple[tuple[str, str, str], ...] = (
    ("Load business data", "Pick a demo business or upload and validate your own files.", "Finance Ops, Owner"),
    ("Forecast cash", "A deterministic weekly forecast with P10, P50 and P90 uncertainty.", "Everyone"),
    ("Spot the shortage", "See the first week below reserve and the funding gap.", "Everyone"),
    ("Compare plans", "Do nothing, collect and optimise, partial or full financing, in the Decision Lab.", "Finance Ops, Owner"),
    ("Review financing", "Check cost, repayment capacity and the readiness indicator.", "Everyone"),
    ("Approve and audit", "The owner approves drafts; every step is written to the hash-chained audit log.", "Owner, Auditor"),
)
TRUST: tuple[tuple[str, str, str], ...] = (
    ("database", "Synthetic data only", "Every number is labelled as demo data."),
    ("ban", "No money movement", "Moving money is denied for every role."),
    ("link", "Hash-chained audit log", "Tampering is detected and shown."),
    ("globe", "Works offline", "No CDN, no external calls."),
)
LAYERS = (
    ("ACTUAL", "recorded data", "actual"), ("FORECAST", "engine output", "forecast"),
    ("HYPOTHETICAL", "what-if plans", "hypo"), ("CONFIRMED", "owner-approved", "confirm"),
)


def hero_art_css() -> str:
    """The hero backdrop as a CSS background image (inline SVG data URI, no files, no network).

    Business theme: faint grid, a cash line with a dip and recovery, bars, coin stack and an invoice card.
    Colours come from app/charts.py so no colour is hard-coded here.
    """
    white = "rgba(255,255,255,"
    grid = "".join(f'<line x1="0" y1="{y}" x2="1200" y2="{y}" stroke="{white}.06)"/>' for y in range(40, 520, 60))
    bars = "".join(
        f'<rect x="{640 + i * 54}" y="{520 - h}" width="32" height="{h}" rx="8" fill="{white}{0.05 + 0.012 * i:.3f})"/>'
        for i, h in enumerate((80, 120, 100, 160, 140, 200, 180, 240, 220, 280))
    )
    coins = "".join(
        f'<ellipse cx="1090" cy="{150 - i * 16}" rx="46" ry="14" fill="none" stroke="{white}.28)" stroke-width="2"/>' for i in range(4)
    )
    amber, green = charts.AMBER, charts.GREEN_500
    svg_markup = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 520" preserveAspectRatio="xMaxYMid slice">'
        f'<circle cx="1010" cy="120" r="300" fill="{green}" fill-opacity=".16"/>'
        f'<circle cx="1180" cy="470" r="220" fill="{amber}" fill-opacity=".07"/>' + grid + bars +
        f'<path d="M520 420 L600 390 L680 410 L760 330 L840 360 L920 270 L1000 232 L1080 176 L1200 120 L1200 520 L520 520 Z" fill="{white}.05)"/>'
        f'<polyline points="520,420 600,390 680,410 760,330 840,360 920,270 1000,232 1080,176 1200,120" fill="none" stroke="{amber}" '
        'stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="680" cy="410" r="9" fill="{amber}"/><circle cx="680" cy="410" r="20" fill="none" stroke="{amber}" stroke-opacity=".45" stroke-width="2"/>'
        + coins +
        f'<rect x="860" y="380" width="170" height="104" rx="14" fill="{white}.06)" stroke="{white}.22)" stroke-width="2"/>'
        f'<line x1="882" y1="410" x2="980" y2="410" stroke="{white}.35)" stroke-width="5" stroke-linecap="round"/>'
        f'<line x1="882" y1="434" x2="1008" y2="434" stroke="{white}.2)" stroke-width="5" stroke-linecap="round"/>'
        f'<line x1="882" y1="458" x2="950" y2="458" stroke="{white}.2)" stroke-width="5" stroke-linecap="round"/>'
        "</svg>"
    )
    return (
        '<style>.st-key-sa-hero{background-image:url("data:image/svg+xml;utf8,' + quote(svg_markup, safe="/:=,()' ")
        + '"),linear-gradient(125deg,var(--green-800) 0%,var(--green-900) 58%,var(--green-950) 100%);'
        "background-repeat:no-repeat;background-position:right center,center;background-size:cover,cover;}</style>"
    )


def _section_head(anchor: str, eyebrow: str, title: str, lead: str) -> None:
    _md(
        f'<div class="sa-sec-head"><div id="{anchor}" class="sa-anchor"></div><div class="sa-eyebrow">{_e(eyebrow)}</div>'
        f'<div class="sa-section" style="margin-top:0">{_e(title)}</div><div class="sa-lead">{_e(lead)}</div></div>'
    )


def _flow_html() -> str:
    cells = "".join(
        f'<div class="sa-step"><div class="no">{i}</div><div class="st">{_e(t)}</div><div class="sd">{_e(d)}</div>'
        f'<div class="sr">{ui._badge(who, "muted")}</div></div>'
        for i, (t, d, who) in enumerate(STEPS, 1)
    )
    return '<div class="sa-flow">' + cells + "</div>"


_LAYER_LINES = {  # layer -> (colour token, stroke-dasharray, marker)
    "ACTUAL": ("var(--green-700)", "", False), "FORECAST": ("var(--green-500)", "7 5", False),
    "HYPOTHETICAL": ("var(--amber)", "10 4 2 4", False), "CONFIRMED": ("var(--green-900)", "", True),
}


def _layers_html() -> str:
    """Four layer cards, each with a line swatch that matches the chart style for that layer."""
    cards = []
    for name, meaning, _tone in LAYERS:
        colour, dash, marker = _LAYER_LINES[name]
        dots = '<path d="M30 3l4 4-4 4-4-4z" fill="currentColor"/>' if marker else ""
        swatch = (
            '<svg viewBox="0 0 60 14" width="60" height="14" aria-hidden="true"><line x1="2" y1="7" x2="58" y2="7" stroke="currentColor" '
            'stroke-width="3" stroke-linecap="round"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>" + dots + "</svg>"
        )
        cards.append(f'<div class="sa-layer" style="--lc:{colour}">{swatch}<b>{_e(name)}</b><span>{_e(meaning.capitalize())}</span></div>')
    return '<div class="sa-layers">' + "".join(cards) + "</div>"


def role_lists(role: str) -> tuple[list[str], list[str]]:
    """Plain-English can / cannot lists derived from the backend permission registry."""
    can, cannot = [], []
    for action, rule in ACTION_REGISTRY.items():
        if rule.tier == "MONEY_MOVEMENT":
            continue
        (can if ui.role_can(role, action) else cannot).append(rule.description)
    return can, cannot


def _role_parts(role: str) -> tuple[str, str]:
    """(head, lists) HTML for a role card. The head has a fixed height so buttons placed under it align across cards."""
    label, ic, desc = ui.ROLE_INFO[role]
    can, cannot = role_lists(role)
    can_html = "".join(f'<li class="y">{_e(t)}</li>' for t in can[:4]) + (f'<li class="y">+{len(can) - 4} more</li>' if len(can) > 4 else "")
    no_html = "".join(f'<li class="n">{_e(t)}</li>' for t in cannot[:3]) + (f'<li class="n">+{len(cannot) - 3} more restricted</li>' if len(cannot) > 3 else "")
    pages = ui.role_pages(role)
    head = f'<div class="sa-role"><div class="sa-role-name">{svg(ic, 22)}{_e(label)}</div><div class="sa-role-desc">{_e(desc)}</div></div>'
    lists = (
        f'<div class="sa-role"><div class="sa-role-h can">Can</div><ul>{can_html}</ul>'
        f'<div class="sa-role-h no">Cannot</div><ul>{no_html or "<li class=n>Nothing restricted</li>"}</ul>'
        f'<div class="sa-card-sub" style="margin-top:8px">Opens {len(pages)} of {len(ui.PAGES)} workspace pages</div></div>'
    )
    return head, lists


def _role_html(role: str) -> str:
    head, lists = _role_parts(role)
    return head + lists


def _demo_login(role: str) -> None:
    try:
        login_demo(role)
        st.session_state["sa_view"] = "home"
        st.rerun()
    except AuthenticationError as exc:
        st.error(str(exc))
    except Exception:  # noqa: BLE001 - keep audit storage details out of the screen
        st.error("Demo sign-in could not be completed. Check the local audit service and try again.")


def render_home() -> None:
    """The home page is public, and its feature shortcuts work for signed-in roles."""
    user = current_user()
    allowed_pages = set(ui.role_pages(user.role)) if user else set()
    allowed_paths = {path for title, path, _icon in ui.PAGES if title in allowed_pages}
    _md(hero_art_css())
    with st.container(key="sa-hero"):
        _md(
            '<div class="sa-hero-copy"><div class="sa-chip-row"><span class="sa-badge sa-chip-glass">Synthetic data</span>'
            '<span class="sa-badge sa-chip-glass">Offline-capable</span><span class="sa-badge sa-chip-glass">No real payments</span></div>'
            '<div class="sa-hero-title">Know your cash gap before it happens.</div>'
            f'<div class="sa-hero-tagline">{_e(ui.TAGLINE)}</div>'
            '<div class="sa-hero-sub">Forecast weekly cash, detect the shortage week, compare four plans and decide with evidence.</div></div>'
        )
        if st.button("Explore Decision Lab", key="hero-cta-lab"):
            if user is None:
                ui.goto_login("pages/lab.py", "Sign in to open Decision Lab.")
            elif "pages/lab.py" in allowed_paths:
                st.switch_page("pages/lab.py")
            else:
                st.warning(f"Decision Lab is not available for the {user.role} role.")
        if user is None and st.button("Sign in", key="hero-cta-signin"):
            ui.goto_login()
        for column, (key, title, desc, ic, path) in zip(st.columns(5, gap="small"), FEATURES):
            with column, st.container(key=f"feat-{key}"):
                _md(f'<div class="ft"><span class="fi">{svg(ic, 18)}</span>{_e(title)}</div><div class="fd">{_e(desc)}</div>')
                if st.button("Open", key=f"fbtn-{key}", use_container_width=True):
                    if user is None:
                        ui.goto_login(path, f"Sign in to open {title}.")
                    elif path in allowed_paths:
                        st.switch_page(path)
                    else:
                        st.warning(f"{title} is not available for the {user.role} role.")

    if user and st.button("Open Overview dashboard", key="home-dashboard"):
        st.switch_page("pages/overview.py")

    _section_head("sa-features", "What it answers", "Five questions every SME owner asks",
                  "Each question is answered by a computed result with its assumptions and sources visible, never by a guess.")
    cards = "".join(
        f'<div class="sa-card sa-q"><div class="qi">{svg(ic, 20)}</div><div class="qt">{_e(q)}</div><div class="qd">{_e(d)}</div>'
        f'<div class="qp">Answered in {_e(page)}</div></div>'
        for q, d, ic, page, _path in QUESTIONS
    )
    _md('<div class="sa-grid">' + cards + "</div>")

    _section_head("sa-how", "How it works", "From raw data to an approved decision in six steps",
                  "The same path every time, so anyone on the team can follow what was decided and why.")
    _md(_flow_html())
    _md('<div class="sa-card-sub" style="margin-top:16px">Every number carries one of four layers, so recorded facts are never confused with what-ifs:</div>' + _layers_html())

    _section_head("sa-roles", "Who can do what", "Four roles, one backend-enforced permission model",
                  "Pick a role to try the product. Each card is generated from the same registry the backend uses.")
    _md(
        '<div class="sa-roles-note">' + svg("info", 18) + "<span>You can read this page without signing in. Opening any workspace page "
        "needs a sign-in, and permissions are enforced by the backend, not by this interface.</span></div>"
    )
    for column, role in zip(st.columns(4, gap="small"), ROLES):
        with column, st.container(key=f"role-{role}"):
            head, lists = _role_parts(role)
            _md(head)
            label = ui.ROLE_INFO[role][0]
            if st.button(f"Continue as {label} (DEMO)", key=f"demo-login-{role}", type="primary", use_container_width=True):
                _demo_login(role)
            if st.button("Sign in with password", key=f"rsign-{role}", use_container_width=True):
                st.session_state["login_prefill"] = role
                ui.goto_login()
            _md(lists)

    _md('<div class="sa-sec-head"><div class="sa-section" style="margin-top:0">Built to be trusted</div></div><div class="sa-trust">' + "".join(
        f'<div><div class="ti">{svg(ic, 20)}</div><div><b>{_e(t)}</b><span>{_e(d)}</span></div></div>' for ic, t, d in TRUST
    ) + "</div>")
    ui.footer()


def render_login() -> None:
    """Two-panel sign-in screen: brand on the left, form and demo roles on the right."""
    left, right = st.columns([5, 6], gap="large")
    with left, st.container(key="login-brand"):
        _md(
            logo_mark(46) + '<div class="sa-login-title">Decisions you can defend, backed by evidence.</div>'
            f'<div class="sa-hero-tagline">{_e(ui.TAGLINE)}</div>'
            + "".join(
                f'<div class="sa-login-li"><span class="ic">{svg(ic, 18)}</span><span>{_e(t)}</span></div>'
                for ic, t in (
                    ("trend", "See the cash gap weeks before it arrives."),
                    ("flask", "Compare plans with costs, risks and assumptions."),
                    ("shield", "Every action needs owner approval and is audited."),
                )
            )
        )
    with right, st.container(key="login-card"):
        _md('<div class="sa-login-h">Sign in</div><div class="sa-card-sub">DEMO authentication for the synthetic-data prototype. '
            "Use the credentials configured in .env or the labelled demo defaults.</div>")
        notice = st.session_state.get("login_notice")
        if notice:
            _md('<div class="sa-login-note">' + _e(notice) + "</div>")
        prefill = st.session_state.get("login_prefill") or ""
        with st.form("login-form"):
            username = st.text_input("Username", value=prefill, key="login-username")
            password = st.text_input("Password", type="password", key="login-password")
            submitted = st.form_submit_button("Sign in", key="login-submit", type="primary", use_container_width=True)
        if submitted:
            try:
                login(username, password)
                st.session_state["sa_view"] = "home"
                st.session_state["login_notice"] = None
                st.rerun()
            except AuthenticationError as exc:
                st.error(str(exc))
            except Exception:  # noqa: BLE001 - hide database/provider details from the login screen
                st.error("Sign in could not be completed. Check the local audit service and try again.")
        _md('<div class="sa-divider-text">or try a demo role</div>')
        for pair in (ROLES[:2], ROLES[2:]):
            for column, role in zip(st.columns(2, gap="small"), pair):
                label, _ic, _desc = ui.ROLE_INFO[role]
                if column.button(f"Continue as {label}", key=f"demo-login-{role}", use_container_width=True):
                    _demo_login(role)
        if st.button("Back to overview", key="login-back"):
            st.session_state["sa_view"] = "home"
            st.session_state["login_notice"] = None
            st.rerun()


def how_it_works_signed_in(user: Any, visible: set[str]) -> None:
    """Tab content for signed-in users: the flow, what their role can do, and shortcuts to the features."""
    _md('<div class="sa-eyebrow">The flow</div><div class="sa-section" style="margin-top:0">From data to an approved decision</div>')
    _md(_flow_html())
    _md('<div class="sa-card-sub" style="margin-top:12px">Data layers used in every chart:</div>' + _layers_html())
    label = ui.ROLE_INFO[user.role][0]
    _md(f'<div class="sa-section">What the {_e(label)} role can do</div><div class="sa-grid">' + f'<div class="sa-card">{_role_html(user.role)}</div></div>')
    _md('<div class="sa-section">Jump to a feature</div>')
    cols = st.columns(len(FEATURES), gap="small")
    for column, (key, title, desc, ic, path) in zip(cols, FEATURES):
        with column, st.container(key=f"card-jump-{key}"):
            _md(f'<div class="sa-q"><div class="qi">{svg(ic, 20)}</div><div class="qt">{_e(title)}</div><div class="qd">{_e(desc)}</div></div>')
            if path in visible:
                if st.button("Open", key=f"jump-{key}", use_container_width=True):
                    st.switch_page(path)
            else:
                st.caption("Not available for your role")
