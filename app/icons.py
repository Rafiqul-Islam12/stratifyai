"""Inline SVG icon set for custom HTML components (no font files, no external assets).

Icons use ``currentColor`` so CSS decides their colour. Paths are drawn on a
24x24 grid with a 1.8 stroke. Streamlit's own widgets use Material icons via
the ``:material/...:`` syntax instead.
"""
from __future__ import annotations

_PATHS: dict[str, str] = {
    "home": '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    "trend": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "flask": '<path d="M9 3h6"/><path d="M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2.2h12.4a1.5 1.5 0 0 0 1.3-2.2L14 9V3"/><path d="M7.5 15h9"/>',
    "bank": '<path d="M3 21h18"/><path d="M5 21V10"/><path d="M9 21V10"/><path d="M15 21V10"/><path d="M19 21V10"/><path d="M12 3l9 5H3z"/>',
    "sparkles": '<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.4 8-8 9-4.6-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5L15.5 10"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.5-3.5 3-5.5 6.5-5.5s6 2 6.5 5.5"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8"/><path d="M18 14.8c2 .6 3.3 2.4 3.5 5.2"/>',
    "upload": '<path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 16v4h16v-4"/>',
    "sliders": '<path d="M4 6h10"/><path d="M18 6h2"/><circle cx="16" cy="6" r="2"/><path d="M4 12h2"/><path d="M10 12h10"/><circle cx="8" cy="12" r="2"/><path d="M4 18h10"/><path d="M18 18h2"/><circle cx="16" cy="18" r="2"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
    "alert": '<path d="M12 3l10 18H2z"/><path d="M12 10v5"/><path d="M12 18v.01"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9 12h6"/><path d="M9 16h6"/>',
    "bars": '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-8"/><path d="M22 20H2"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "wallet": '<path d="M3 7h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 7l12-3v3"/><path d="M17 14h.01"/>',
    "arrow": '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
    "eye": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c3 3 3 15 0 18-3-3-3-15 0-18z"/>',
    "database": '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "ban": '<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c.7-4 4-6 8-6s7.3 2 8 6"/>',
    "scale": '<path d="M12 3v18"/><path d="M5 21h14"/><path d="M4 7h16"/><path d="M6 7l-3 7a3 3 0 0 0 6 0z"/><path d="M18 7l-3 7a3 3 0 0 0 6 0z"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8v.01"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
}


def svg(name: str, size: int = 20, cls: str = "") -> str:
    """Return one inline SVG string (single line, safe to embed in st.markdown)."""
    body = _PATHS.get(name, _PATHS["target"])
    css = "sa-icon" + (" " + cls if cls else "")
    return (
        f'<svg class="{css}" viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{body}</svg>'
    )


def logo_mark(size: int = 34) -> str:
    """The StratifyAI mark: a rounded green tile with a rising cash line and bars."""
    return (
        f'<svg class="sa-logo-mark" viewBox="0 0 40 40" width="{size}" height="{size}" aria-hidden="true">'
        '<defs><linearGradient id="sa-lg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="var(--green-500)"/><stop offset="1" stop-color="var(--green-700)"/>'
        '</linearGradient></defs>'
        '<rect width="40" height="40" rx="11" fill="url(#sa-lg)"/>'
        '<rect x="9" y="22" width="4.5" height="9" rx="1.4" fill="rgba(255,255,255,.55)"/>'
        '<rect x="17.7" y="17" width="4.5" height="14" rx="1.4" fill="rgba(255,255,255,.78)"/>'
        '<rect x="26.4" y="11" width="4.5" height="20" rx="1.4" fill="#fff"/>'
        '<path d="M9 17.5l7-5 6 3.5 9-8" fill="none" stroke="var(--amber)" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )
