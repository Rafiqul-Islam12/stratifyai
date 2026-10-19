"""Shared Plotly theme and the four-layer colour constants.

All chart colours come from here, so no page or chart function ever hard-codes
a colour. Values mirror the CSS tokens in app/styles.css (green + off-white).
The layer meanings are fixed (see docs/DESIGN.md and docs/UI_REDESIGN.md) and are
distinguished by dash and marker as well as colour:

    ACTUAL       solid deep green    - recorded data
    FORECAST     dashed mid green    - engine output
    HYPOTHETICAL dash-dot amber      - what-if changes
    CONFIRMED    solid dark + marker - owner-approved
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# tokens (mirror app/styles.css)
# ---------------------------------------------------------------------------
PRIMARY = "#0F6A52"
GREEN_900 = "#064032"
GREEN_500 = "#2F9E7A"
GREEN_300 = "#7AA299"
GREEN_100 = "#DCF2E5"
AMBER = "#DCA763"
INFO = "#2E7C8F"
BACKGROUND = "#FAF7F2"
SURFACE = "#FFFBF8"
BORDER = "#E9E4DB"
TEXT = "#14231D"
MUTED = "#5E6F67"
GRID = "#EEEAE2"

FONT_FAMILY = "Inter, Segoe UI Variable, Segoe UI, system-ui, Roboto, Helvetica Neue, Arial, sans-serif"
FONT_SIZE = 12

LAYER_ACTUAL = "ACTUAL"
LAYER_FORECAST = "FORECAST"
LAYER_HYPOTHETICAL = "HYPOTHETICAL"
LAYER_CONFIRMED = "CONFIRMED"

LAYER_STYLES: Mapping[str, Mapping[str, Any]] = {
    LAYER_ACTUAL: {"color": PRIMARY, "dash": "solid"},
    LAYER_FORECAST: {"color": GREEN_500, "dash": "dash"},
    LAYER_HYPOTHETICAL: {"color": AMBER, "dash": "dashdot"},
    LAYER_CONFIRMED: {"color": GREEN_900, "dash": "solid"},
}
BAND_COLOR = "rgba(47,158,122,0.16)"
RESERVE_COLOR = MUTED
SHORTAGE_COLOR = "#C2412D"
SHORTAGE_FILL = "rgba(194,65,45,0.10)"
PALETTE = (PRIMARY, GREEN_500, GREEN_300, AMBER, INFO, MUTED)


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
        title=dict(text=f"<b>{title}</b>" if title else None, x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=FONT_SIZE + 3, color=TEXT)),
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=list(PALETTE),
        font=dict(family=FONT_FAMILY, size=FONT_SIZE, color=TEXT),
        margin=dict(l=56, r=20, t=76 if title else 44, b=52),
        hovermode="x unified",
        bargap=0.35,
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=BORDER, font=dict(family=FONT_FAMILY, size=12, color=TEXT)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=11, color=MUTED),
                    itemsizing="constant", bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=True, linecolor=BORDER,
                     tickfont=dict(color=MUTED), title_font=dict(color=MUTED, size=11))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, showline=False, tickfont=dict(color=MUTED),
                     title_font=dict(color=MUTED, size=11), hoverformat=",.0f")
    return fig


def polish(fig: go.Figure) -> go.Figure:
    """Final pass before display: rounded bars and sensible hover for horizontal bars."""
    try:
        fig.update_traces(selector=dict(type="bar"), marker_cornerradius=6)
    except (ValueError, TypeError):  # older Plotly without marker.cornerradius
        pass
    if any(getattr(t, "type", "") == "bar" and getattr(t, "orientation", None) == "h" for t in fig.data):
        fig.update_layout(hovermode="closest")
        fig.update_xaxes(showgrid=True, gridcolor=GRID)
        fig.update_yaxes(showgrid=False)
    return fig


def line(fig: go.Figure, x: Sequence[Any], y: Sequence[Any], *, layer: str, name: str | None = None) -> None:
    """Add a line coloured by its layer. Unknown layers raise KeyError."""
    style = LAYER_STYLES[layer]
    marker = dict(symbol="diamond", size=7, color=style["color"]) if layer == LAYER_CONFIRMED else None
    fig.add_scatter(
        x=x,
        y=y,
        mode="lines+markers" if marker else "lines",
        name=name or layer,
        marker=marker,
        line=dict(color=style["color"], width=2.6, dash=style["dash"]),
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
        marker=dict(color=SHORTAGE_COLOR, size=10, line=dict(color=SURFACE, width=2)),
        name="Shortage",
        hovertemplate="%{text}<extra></extra>",
        text=["Shortage"],
    )


def donut(labels: Sequence[str], values: Sequence[float], *, center: str = "", height: int = 300) -> go.Figure:
    """Donut for composition (income / expense by category) with a total in the centre."""
    fig = go.Figure(go.Pie(
        labels=list(labels), values=list(values), hole=0.66, sort=False, direction="clockwise",
        marker=dict(colors=list(PALETTE) * 3, line=dict(color=SURFACE, width=2)),
        textinfo="none", hovertemplate="%{label}<br>BDT %{value:,.0f} (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_white", height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY, size=FONT_SIZE, color=TEXT), margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(orientation="v", font=dict(size=11, color=MUTED), bgcolor="rgba(0,0,0,0)"),
        annotations=[dict(text=center, x=0.5, y=0.5, showarrow=False, font=dict(size=15, color=TEXT))] if center else [],
    )
    return fig


def gauge(value: float | None, *, label: str = "", height: int = 240) -> go.Figure:
    """Semi-circle gauge for a 0-100 indicator (financing readiness)."""
    shown = 0.0 if value is None else float(value)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=shown, number=dict(suffix=" / 100" if value is not None else "", font=dict(size=30, color=TEXT)),
        title=dict(text=label, font=dict(size=13, color=MUTED)),
        gauge=dict(
            axis=dict(range=[0, 100], tickfont=dict(color=MUTED, size=10)), bar=dict(color=PRIMARY, thickness=0.28),
            bgcolor=GREEN_100, borderwidth=0,
            steps=[dict(range=[0, 40], color=SHORTAGE_FILL), dict(range=[40, 70], color="rgba(220,167,99,0.25)"),
                   dict(range=[70, 100], color=GREEN_100)],
        ),
    ))
    fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)", font=dict(family=FONT_FAMILY, color=TEXT),
                      margin=dict(l=24, r=24, t=48, b=8))
    return fig
