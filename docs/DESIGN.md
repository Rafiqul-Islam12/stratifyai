# DESIGN SYSTEM (single source of truth for UI)

> **Superseded for colour, typography and layout by `docs/UI_REDESIGN.md` (UI v2: green + off-white, fixed navbar and
> sidebar, card grid, public Overview, sign-in screen).** The token table below is the old indigo/teal system; keep it
> only for the four-layer meanings and the component list. Where the two disagree, UI_REDESIGN.md wins.

Goal: clean, premium, judge-impressive, consistent. Designed for a 1440px wide screen (presentation), layout="wide". English UI.

## Tokens (define once in app/styles.css as CSS variables and in .streamlit/config.toml; never hard-code colours elsewhere)
- Brand gradient (logo, hero strip, active nav item only): Indigo #4F46E5 to Teal #14B8A6
- Background #F8FAFC, Surface #FFFFFF, Border #E2E8F0
- Text #0F172A, Muted #64748B
- Success #16A34A, Warning #F59E0B, Danger #DC2626, Info #2563EB
- Radius 12px, soft shadow (0 1px 3px rgba(15,23,42,0.08)), spacing scale 4/8/12/16/24/32

## Four-layer chart colours (same meaning on every page)
- ACTUAL: solid #1E3A8A
- FORECAST: dashed #4F46E5
- Uncertainty band P10 to P90: rgba(79,70,229,0.15)
- HYPOTHETICAL (what-if): dashed #14B8A6
- CONFIRMED (owner-approved): solid #15803D
- Minimum reserve: dashed #F59E0B
- Shortage region: rgba(220,38,38,0.12) shading, shortage marker #DC2626
Every chart shows a small legend of these layers. Plotly theme comes from one function in app/charts.py (same font, grid, margins, hover format).

## Typography
Inter (self-hosted woff2 via Streamlit static file serving and [[theme.fontFaces]]; fallback: system-ui stack). Scale: 12 caption, 14 body, 16 emphasis, 20 section title, 28 page title, 36 hero number. Weights 400/500/600/700. Numbers use tabular-nums. Currency format "BDT 1,234,567" with thousands separators; percentages with one decimal.

## Layout
- Left sidebar: StratifyAI wordmark with gradient accent, tagline, navigation (10 pages with icons), bottom: current user and role badge, "Synthetic data" badge.
- Header band on every page: page title and one-line purpose; right side: business selector, scenario label, alert indicator.
- Main area: 12-column rhythm using st.columns; consistent 24px vertical spacing; cards use bordered containers with the shared card style.
- Footer on every page: "StratifyAI | Synthetic data, not financial advice | Illustrative financing terms | v<version>".
- Hide default Streamlit menu, deploy button and footer.

## Pages (navigation order)
1. Overview 2. Cash Flow 3. Liquidity Decision Lab 4. Financing 5. Business Analysis 6. Copilot 7. Approvals and Audit 8. Data Upload 9. Assumptions 10. Security

## Components (app/components.py, reused by every page)
page_header, kpi_card (label, value, delta, tooltip), alert_banner (info/warning/critical), section_title, plan_card (Lab option card), badge (layer or status), empty_state (with call to action), info_tooltip, layer_legend, footer.

## States and interaction
Every page has: loading state (st.spinner/status), empty state ("No data loaded" with a "Load demo business" button), friendly error state (no stack traces). Dynamic: sliders and inputs recalculate instantly (cache heavy computation with st.cache_data; use st.fragment where useful). Alert click-through to the Lab (st.switch_page). Dialogs (st.dialog) for approvals. Editable tables with st.data_editor for assumptions.

## Overview page content (everything at a glance)
1. Alert banner: shortage week, amount, probability. 2. Six KPI cards: current cash, minimum projected balance and week, funding gap, runway (weeks), overdue receivables, DSO. 3. Hero chart: actual + forecast + P10-P90 band + reserve + shortage shading. 4. Recommended plan card with "Open Decision Lab" button. 5. Financing readiness indicator. 6. Receivables aging chart. 7. Pending approvals and latest audit events. 8. Data source badge and "Load demo business" selector.

## Extra UI options (small, high-impact)
- Security page: System Status panel (cards: app version, data mode "Synthetic", copilot mode, audit chain OK/broken, last test run, fonts local), Role preview table (what each role may do, read from the permissions registry), tier table.
- Copilot page: Copilot Receipt expander under every answer.
- Business Analysis: receivables watchlist table with coloured labels and evidence links.
- Financing page: readiness indicator and "Download readiness pack" with hash and "Verify pack" tool.
- Lab page: "Download decision report" button.

## Quality bar
Consistent alignment and spacing; no raw numbers without units; no placeholder text in final UI; no overlapping elements at 1440px; contrast AA for text; every metric has a tooltip explaining its formula or source.
