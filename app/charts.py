"""Shared Plotly theme and the four-layer colour constants (T02).

All chart colours come from here, so no page or chart function ever hard-codes
a colour. The layer meanings are fixed by docs/DESIGN.md:

    ACTUAL       solid navy      - recorded data
    FORECAST     dashed indigo   - engine output
    HYPOTHETICAL dashed teal     - what-if changes
    CONFIRMED    solid green     - owner-approved
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# tokens (mirror app/styles.css)
# ---------------------------------------------------------------------------
PRIMARY = "#4F46E5"
BACKGROUND = "#F8FAFC"
SURFACE = "#FFFFFF"
BORDER = "#E2E8F0"
TEXT = "#0F172A"
MUTED = "#64748B"
GRID = "#F1F5F9"

FONT_FAMILY = "Inter, system-ui, Segoe UI, Helvetica Neue, Arial, sans-serif"
FONT_SIZE = 12

LAYER_ACTUAL = "ACTUAL"
LAYER_FORECAST = "FORECAST"
LAYER_HYPOTHETICAL = "HYPOTHETICAL"
LAYER_CONFIRMED = "CONFIRMED"

LAYER_STYLES: Mapping[str, Mapping[str, Any]] = {
    LAYER_ACTUAL: {"color": "#1E3A8A", "dash": "solid"},
    LAYER_FORECAST: {"color": PRIMARY, "dash": "dash"},
    LAYER_HYPOTHETICAL: {"color": "#14B8A6", "dash": "dash"},
    LAYER_CONFIRMED: {"color": "#15803D", "dash": "solid"},
}
BAND_COLOR = "rgba(79,70,229,0.15)"
RESERVE_COLOR = "#F59E0B"
SHORTAGE_COLOR = "#DC2626"
SHORTAGE_FILL = "rgba(220,38,38,0.12)"


def base_layout(
    *,
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    height: int = 360,
) -> go.Figure:
    """A figure pre-styled with the shared font, grid, margins and hover format."""
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        title=title or None,
        title_font=dict(size=FONT_SIZE + 4, color=TEXT),
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=height,
        font=dict(family=FONT_FAMILY, size=FONT_SIZE, color=TEXT),
        margin=dict(l=60, r=24, t=48, b=56),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=BORDER, font=dict(family=FONT_FAMILY, size=12)),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=BORDER, linecolor=BORDER)
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=1.0, x=0, font=dict(size=11)))
    return fig


def line(fig: go.Figure, x: Sequence[Any], y: Sequence[Any], *, layer: str, name: str | None = None) -> None:
    """Add a line coloured by its layer. Unknown layers raise KeyError."""
    style = LAYER_STYLES[layer]
    fig.add_scatter(
        x=x,
        y=y,
        mode="lines",
        name=name or layer,
        line=dict(color=style["color"], width=2.5, dash=style["dash"]),
    )


def band(fig: go.Figure, x: Sequence[Any], lower: Sequence[Any], upper: Sequence[Any]) -> None:
    """Add the P10-P90 uncertainty band."""
    fig.add_scatter(x=x, y=lower, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_scatter(
        x=x,
        y=upper,
        mode="lines",
        line=dict(width=0),
        name="P10-P90",
        fill="tonexty",
        fillcolor=BAND_COLOR,
        hoverinfo="skip",
    )


def reserve(fig: go.Figure, x: Sequence[Any], value: float) -> None:
    """Add the minimum-reserve reference line."""
    fig.add_hline(
        y=value,
        line=dict(color=RESERVE_COLOR, dash="dash", width=1.5),
        annotation_text="Reserve",
        annotation_font_color=RESERVE_COLOR,
    )


def shortage(fig: go.Figure, from_x: Any, to_x: Any) -> None:
    """Shade the region below the minimum reserve."""
    fig.add_vrect(x0=from_x, x1=to_x, fillcolor=SHORTAGE_FILL, line_width=0, layer="below")


def shortage_marker(fig: go.Figure, x: Any, y: float) -> None:
    """Mark the shortage week."""
    fig.add_scatter(
        x=[x],
        y=[y],
        mode="markers",
        marker=dict(color=SHORTAGE_COLOR, size=9),
        name="Shortage",
        hovertemplate="%{text}<extra></extra>",
        text=["Shortage"],
    )
