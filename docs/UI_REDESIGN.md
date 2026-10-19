# UI REDESIGN SPEC (single source of truth for the redesign)

Save this file as `docs/UI_REDESIGN.md`. It supersedes the colour, typography and layout parts of `docs/DESIGN.md`.
Everything in CLAUDE.md "Non-negotiable product rules" still applies (offline, no CDN, numbers only from `core/`, four layers, permissions in `services/`).

## 0. Scope and ground rules

- This is a **UI-only redesign**. Do NOT change `core/` logic, `services/` security logic, permission rules, datasets, audit, or any computed number. UI glue code is fine.
- The redesign is an approved out-of-plan job (phases UI-1 to UI-5). It overrides the "one task per turn / wait for `next`" rule, but you must still: checkpoint in `docs/PROGRESS.md`, commit per phase, keep `pytest -q`, `ruff check .`, `python run.py check` and `python scripts/check_secrets.py` green.
- Stack stays: Python 3.11, Streamlit 1.66.0 (pinned), plotly 7.1.0. Add no dependency. No CDN, no Google Fonts, no remote images, no external URL anywhere (a test enforces this). Everything must work offline.
- English UI only. Keep title "StratifyAI" and tagline "The Liquidity Decision Lab for SME Financial Intelligence" (rule 12). Keep the "Synthetic data" labelling and the footer disclaimer.
- Reference images (open and study every one before coding):
  - `docs/inputs/UI Sample/` : **colour palette, mood, layout, sidebar, hero card, card style** (green + off-white). This is the primary reference.
  - `docs/inputs/Others Sample/` : **chart styles, KPI card patterns, alignment, spacing, font sizes, table styling, sidebar grouping**. Take the structure and chart styling from them, but NOT their purple/blue colours.
  - If you cannot view images, rely on the palette and layout notes below, which were extracted from them.

## 1. Diagnosis of the current UI (root causes to fix)

1. **Top of every page is clipped.** `styles.css` forces `[data-testid="stMainBlockContainer"] { padding: 12px 24px !important }` while Streamlit's header overlays the top, so the first lines (context bar, title) are cut off or hidden.
2. **Duplicate and stacked controls before the content.** The global context bar (Business, Scenario, role) renders above every page; most pages also have their own case selectbox (`overview-case-select`, `cashflow-case-select`, ...), a header band repeating business/scenario, and a caption. The real title starts far down.
3. **Inconsistent type.** Inter is not installed (`static/fonts/` is empty) so the system font is used; KPI values are 16-20px, card hero values 36px, Streamlit widgets default 14-16px, chart text 12px, captions everywhere. Nothing follows one scale.
4. **Wrong palette.** Indigo/teal brand in `styles.css`, `charts.py`, `.streamlit/config.toml`. Target is green + off-white.
5. **Fake cards.** Cards are HTML strings, so charts and widgets cannot live inside a card; mixing `st.columns` with HTML cards gives uneven heights and misalignment.
6. **Sidebar.** Collapsible, emoji icons, flat list of 10 links, user/role and a default-styled "Log out" button at the bottom. Needs to be fixed, grouped and branded.
7. **Overview needs login**, so visitors see nothing; there is no explanation of features, flow or roles, and no clear "what needs sign-in".
8. **Very long pages.** e.g. Decision Lab opens an assumptions expander (`expanded=True`) above everything, followed by ~8 stacked sections. Users scroll a lot and cannot find options.

## 2. Design tokens (define once in `app/styles.css` as CSS variables and mirror in `charts.py` and `.streamlit/config.toml`; never hard-code colours elsewhere)

Palette (sampled from the UI Sample image):

| Token | Hex | Use |
| --- | --- | --- |
| `--green-950` | #04291F | deepest text on light green, hero shadow |
| `--green-900` | #064032 | top navbar, hero end colour |
| `--green-800` | #0A4D3C | hero start colour, dark cards |
| `--green-700` | #0F6A52 | primary buttons, links, ACTUAL line |
| `--green-500` | #2F9E7A | FORECAST line, positive deltas |
| `--green-300` | #7AA299 | muted bars, secondary series |
| `--green-100` | #DCF2E5 | active nav item, selected chips |
| `--green-50`  | #F0F8F3 | hover, soft fills |
| `--cream-50`  | #FFFBF8 | sidebar and card surface |
| `--cream-100` | #FAF7F2 | page background (top) |
| `--cream-200` | #F2F3ED | page background (bottom/right, subtle gradient) |
| `--border`    | #E9E4DB | card and table borders |
| `--text`      | #14231D | body text (warm near-black green) |
| `--muted`     | #5E6F67 | secondary text |
| `--amber`     | #DCA763 | single highlight accent (today bar, flagship badge) |
| `--warning`   | #B7791F | warning text/icon |
| `--danger`    | #C2412D | shortage, errors |
| `--info`      | #2E7C8F | info |

Page background: `linear-gradient(135deg, cream-100, cream-200)` plus one very faint green radial glow in a corner, like the sample.
Radius: 16px cards, 12px inner tiles/inputs, 999px chips. Shadow: `0 1px 2px rgba(6,64,50,.06), 0 8px 24px rgba(6,64,50,.06)`. Border: 1px `--border`.
Spacing scale: 4/8/12/16/24/32/48. Grid gap between cards: 16px (24px between sections).

Typography (all sizes are tokens; **no component may use a font-size outside them**):
- Family: `Inter` self-hosted (see section 9), fallback `system-ui, "Segoe UI", Roboto, Arial, sans-serif`. One family everywhere, including Plotly and Streamlit widgets.
- Fluid scale with `clamp()` and `rem`, so it adapts to screen width and browser zoom:
  - caption `clamp(.75rem, .72rem + .1vw, .8125rem)` (12-13px)
  - body `clamp(.875rem, .85rem + .15vw, .9375rem)` (14-15px)
  - emphasis `1rem`
  - card/section title `clamp(1.0625rem, 1rem + .3vw, 1.25rem)` (17-20px)
  - page title `clamp(1.5rem, 1.3rem + .8vw, 2rem)` (24-32px)
  - KPI value `clamp(1.375rem, 1.2rem + .6vw, 1.75rem)` (22-28px), same in every KPI card
  - hero headline `clamp(2rem, 1.4rem + 2vw, 3.25rem)`; hero number on the dark card up to 3.5rem (only one per page)
- Weights 400/500/600/700. `font-variant-numeric: tabular-nums` on all numbers. Letter-spacing -0.01em on titles.
- Restyle Streamlit's own elements (labels, inputs, selectboxes, sliders, buttons, tabs, expanders, dataframes, captions, alerts, metrics, chat messages) to these tokens, otherwise they will look foreign next to custom components.
- Currency format stays "BDT 1,234,567" (full number, thousands separators). Percent with one decimal. Use compact axis ticks (e.g. 5M) only on chart axes.

## 3. Shell layout

```
┌──────────────────────────── fixed top navbar (60px, --green-900) ───────────────────────────┐
│ [logo] StratifyAI   (public: Overview · Features · How it works · Roles)   [DEMO] [Sign in] │
├───────────────┬──────────────────────────────────────────────────────────────────────────────┤
│ fixed sidebar │  page header (compact)                                                       │
│ 248px         │  content grid (cards)                                                        │
│ cream-50      │  footer                                                                      │
└───────────────┴──────────────────────────────────────────────────────────────────────────────┘
```

**Top navbar (new, on every screen)**
- Fixed, full width, height 60px, background `--green-900`, white text, z-index above everything.
- Left: inline-SVG logo mark (rounded square in green gradient with a small rising-line/bars glyph) + "StratifyAI" wordmark. Clicking it goes to Overview. No image files; draw the SVG inline using CSS variables.
- Middle (logged out): anchor links to the Overview sections: Features, How it works, Roles. (If anchors misbehave in Streamlit, drop them rather than hack.)
- Right: a "Synthetic data" chip; logged out: **Sign in** button (outlined, white); logged in: user chip (display name + role badge) that opens `st.popover` with role summary and **Log out**.
- Build it with `st.container(key="sa-navbar")` + `st.columns`, and style via `.st-key-sa-navbar { position: fixed; ... }` so the real Streamlit buttons live inside it. Hide Streamlit's own header/toolbar (`header[data-testid="stHeader"]`, deploy button, main menu) because the sidebar is no longer collapsible.

**Sidebar (fixed, always open)**
- Fixed under the navbar: `top: 60px; height: calc(100vh - 60px); width: 248px`, internal scroll only if needed. Remove the collapse/expand controls via CSS. Background `--cream-50`, right border.
- Replace emoji with Streamlit Material icons: `st.page_link(..., icon=":material/dashboard:")` etc.
- Group the 10 pages under small uppercase group labels:
  - (none) Overview
  - **Decide**: Decision Lab (flagship, amber "Core" chip), Cash Flow, Financing
  - **Understand**: Analysis, Copilot
  - **Govern**: Approvals, Security
  - **Data**: Data Upload, Assumptions
- Active item: `--green-100` background, `--green-800` text, 3px left accent bar. Hover: `--green-50`.
- Bottom block, pinned: one primary button "Open Decision Lab" (like "New Project" in the samples), then the user card (name, role badge) and "Synthetic data" badge. Logout lives in the navbar popover.
- Logged out: show the sidebar too, with Overview plus the workspace links shown **locked** (lock icon, muted). Clicking a locked item must NOT run the gated page; it opens the sign-in screen with the message "Sign in to open <page>" and, after a successful login, returns to that page (`st.session_state["post_login_target"]`). Role-restricted pages that the signed-in role cannot use (existing `PAGE_ACTIONS`) show locked with a tooltip "Available to: owner, finance_ops".

**Main area**
- Top padding = navbar height + 24px (this is what fixes the clipped title). Left padding comes from the sidebar width. Content max-width 1280px, centred in the remaining area, horizontal padding 32px.
- **Page header** (compact, replaces the old big band): page title (page-title token) + one-line purpose on the left; on the right a chip group: Business selector, Scenario selector, data-mode badge. These two selectors exist **once**, inside this header, driven by the existing session keys (`active_synthetic_case`, `global-business-selector`, `global-scenario-selector`). Remove the per-page case selectboxes and the extra captions; keep the widget keys only if a test needs them, otherwise update the test deliberately.
- Footer unchanged in content, restyled, with generous top margin.

## 4. Component library (`app/components.py`, reused everywhere)

Make real cards: `card(key, title=None, subtitle=None, action=None)` = `st.container(border=True, key=f"card-{key}")` styled through `.st-key-card-*` so charts, tables, widgets can sit inside a card with consistent padding, radius, shadow and a header row (title left, optional chips/legend right). Keep the existing helper names that tests or pages import (`page_header`, `kpi_row`, `kpi_card`, `plan_card`, `plan_row`, `alert_banner`, `section_title`, `badge`, `empty_state`, `layer_legend`, `footer`, `info_tooltip`) and keep their behaviour; restyle and extend them.

New or upgraded components:
- `hero_card` (dark green gradient `--green-800` to `--green-900`, big number + label + mini bar chart on the right, like "Spent in October" in the UI Sample). One per page at most.
- `kpi_grid` : responsive CSS grid `repeat(auto-fit, minmax(220px, 1fr))`, equal heights, same value size, label top, value, delta chip (green up / red down), optional tiny sparkline (inline SVG, CSS variables).
- `chip` / `chip_group` (filter chips and range switches), `status_pill`, `role_badge`.
- `feature_card` (icon, title, one-line description, button/link) used on Overview.
- `flow_steps` : horizontal stepper with numbered nodes joined by a line/arrows, wrapping to two rows on narrow screens.
- `progress_row` : label, value, percent, thin rounded bar (like "Where October went").
- `locked_card` : shown when a role or a signed-out visitor cannot use something: lock icon, who can use it, and a primary "Sign in" action.
- `activity_list` : icon + title + one-line detail + time (for latest audit events and pending approvals).
- `tab_page`: helper that wraps `st.tabs` with the shared tab style (pill tabs, `--green-100` active).
- Tables: `st.dataframe` inside a card, header row `--green-50`, no heavy gridlines, status columns rendered as coloured text/pills (Paid/Due style from the samples) where a status exists.

All user/uploaded text must still go through `_e()` escaping.

## 5. Chart style (`app/charts.py`, one theme function)

Take the look from the Others Sample images:
- Transparent plot and paper background inside cards; no chart border. Only light **horizontal** gridlines (`--border` at low opacity), no vertical grid, no zero-line emphasis, axis lines off. Tick font = caption token, colour `--muted`.
- Legend: small, horizontal, top-left inside the card header area, with round markers. Keep the four-layer legend (`layer_legend`) consistent with the chart colours.
- Hover: `hovermode="x unified"`, white rounded tooltip with soft shadow (like the "Peak Reach" / "August 2026" tooltips), currency formatted `BDT %{y:,.0f}`.
- Bars: rounded corners (`marker.cornerradius`), gap 0.35, the current/selected bar highlighted with `--amber` or `--green-700` and the rest `--green-300` at reduced opacity.
- Lines: width 2.5, area fill under ACTUAL with a very light green, round line caps. Use linear interpolation for financial series (do not smooth forecasts; smoothing implies precision we do not have).
- Composition charts: **donut** with the total in the centre (income/expense by category) plus `progress_row` list beside it; **semi-circle gauge** for the financing readiness score; horizontal bars for rankings.
- Standard heights: hero chart 380, normal chart 300, small chart 220, sparkline 56. Same margins everywhere (l 48, r 16, t 16, b 40) because the card header holds the title.
- Series colours (defined in `charts.py`, same meaning on every page; distinguish by dash/marker as well as colour):
  - ACTUAL solid `--green-700`; FORECAST dashed `--green-500`; uncertainty band P10-P90 `--green-500` at 15% alpha; HYPOTHETICAL dash-dot `--amber`; CONFIRMED solid `--green-900` with diamond markers; minimum reserve dashed slate (`--muted`) with a label; shortage shading `--danger` at 12% alpha and a `--danger` marker.
  - Categorical palette (donuts/bars): `--green-700`, `--green-500`, `--green-300`, `--amber`, `--info`, `--muted`.
- Keep `app/charts.py` importable without Streamlit (a test checks it) and keep `LAYER_STYLES` keys and dash values that tests assert, or update those tests deliberately.

## 6. Public Overview (logged out). This is the first screen for everyone.

One scrolling landing page with four sections and real sub-structure. All copy is English, concrete, no filler.

1. **Hero** (large, ~420-480px tall, dark-green gradient card spanning the content width).
   - Background: an **inline SVG/CSS illustration with a business theme** (faint grid, rising cash-flow line with a dip and recovery, bars, a few coin/receipt/invoice glyphs, soft glow), drawn with CSS variables, no image files, no external assets. Must stay readable behind text.
   - Headline: "Know your cash gap before it happens." Sub-line = official tagline. One short sentence: "Forecast weekly cash, detect the shortage week, compare four plans, and decide with evidence."
   - Primary button "Explore Decision Lab" (amber or white-on-green), secondary "Sign in".
   - **Feature buttons row** (5 cards/buttons in a grid under the headline, frosted-glass style): Liquidity Decision Lab (flagship, highlighted), Cash-Flow Forecast, Financing Advisor, Evidence-grounded Copilot, Approvals & Audit. Each shows an icon, a one-line promise, and navigates to its page. Signed out => goes to sign-in with the "Sign in to open <page>" message and returns after login.
   - A small chip line under it: "Synthetic data · Offline-capable · No real payments".
2. **What it answers** (id `sa-features`): the five questions from the brief as a card grid (When will cash run short? How much funding is needed? Can we avoid borrowing? Which financing options are worth comparing? What if sales fall or payments are late?), each linking to the page that answers it.
3. **How it works** (id `sa-how`): `flow_steps` with six steps: 1 Load business data -> 2 Forecast cash (P10/P50/P90) -> 3 Shortage detected -> 4 Compare plans in the Decision Lab (do nothing / collect & optimise / partial / full financing) -> 5 Review financing and evidence -> 6 Owner approval and audit trail. Under each step: what the user does, and which role can do it. Add a one-line legend explaining the four data layers (ACTUAL, FORECAST, HYPOTHETICAL, CONFIRMED).
4. **Who can do what** (id `sa-roles`): four role cards in a grid: Owner, Finance Ops, Viewer, Auditor. Each card: one-line description, "Can" list, "Cannot" list, pages they see, and two buttons: "Continue as <role> (DEMO)" (uses existing `login_demo`) and "Sign in with password". **Derive the can/cannot text from `services.permissions.ACTION_REGISTRY`** (plain-English labels) so it can never drift from the backend. Add a banner above: "You can read this page without signing in. Opening any workspace page requires signing in; permissions are enforced by the backend, not by this UI."
5. **Trust strip**: four small tiles: Synthetic data only; MONEY_MOVEMENT always denied; Hash-chained audit log; Works offline (no CDN, no external calls). Then footer.

Do not compute or show any real forecast numbers on the public page (use a clearly labelled illustration only).

## 7. Sign-in screen

- Full content-area, centred two-panel card: left panel dark green (brand, tagline, 3 bullet benefits, small illustration reuse); right panel the form: Username, Password, **Sign in** (primary), then a divider "or try a demo role" and four role buttons in a 2x2 grid with a one-line description each. Keep the existing `login`/`login_demo` calls, audit logging, error messages, and the DEMO labelling. Never print passwords.
- Shows the "Sign in to open <page>" notice when arriving from a locked item. After login go to `post_login_target` if set, else Overview.
- Streamlit's default page title/sidebar content must not leak onto this screen.

## 8. Signed-in pages

General rules for every page: compact header; KPI/hero summary first; the main chart next; details below inside **tabs** or collapsed expanders so nothing important is more than one click or one short scroll away; no section longer than ~1.5 screen heights; two-column grid (8/4 or 7/5) instead of a single tall stack; empty states use the shared `empty_state`/`locked_card`; every metric keeps its tooltip.

- **Overview (signed in)**: tabs `Dashboard | How it works & my role`. Dashboard layout: alert banner; row 1 = `hero_card` "Current cash" (with mini weekly bars) on the left and a 2x3 `kpi_grid` of the remaining KPIs; row 2 = hero cash chart (8 cols, ACTUAL + FORECAST + band + reserve + shortage) and Recommended plan + Financing readiness gauge (4 cols); row 3 = receivables aging chart and `activity_list` for pending approvals and latest audit events; a `feature_card` strip "Next steps" at the bottom. The second tab reuses the public flow, roles and "what my role can do" card.
- **Cash Flow**: tabs `Forecast | Weekly table | Assumptions`. Controls (reserve, variability) in a slim control card above the chart, not inside the chart area.
- **Decision Lab (flagship, make it the most polished page)**: top: recommended-plan strip + four plan cards in one equal-height row (Option 0, A, B, C) with the recommended one highlighted; then tabs `Compare | Levers & assumptions | Stress tests | Plan details | Scenarios & proposal`. The assumptions form is no longer an expanded block on top: put it in the "Levers & assumptions" tab (or a right-hand panel). Chart "Balance by plan" is the hero of the Compare tab; cost/gap and lever charts sit beneath in a 2-column row. Download decision report stays as a header button.
- **Financing**: tabs `Cost & repayment | Readiness | Readiness pack`; readiness uses the gauge; parameter inputs in a left control card, results on the right.
- **Analysis**: tabs `Trends | Categories | Receivables | Insights`; donuts + progress rows for categories; watchlist table with coloured status.
- **Copilot**: chat-style layout, suggested questions as chips, answer cards with the receipt in a collapsed expander. Keep the form/keys used by tests, or update tests deliberately.
- **Approvals**: tabs `Create draft | Pending queue | My drafts | Audit log`; queue as list cards with status pills and Approve/Reject buttons (dialogs kept).
- **Data Upload**: 3-step stepper (Template -> Upload -> Validate and use); validation results as KPI chips; preview table in a card.
- **Assumptions**: tabs `Forecast | Lab levers | Financing | Stress | Import case | Sources`; two-column forms, labels aligned, units shown in the label.
- **Security**: tabs `Status | Roles & permissions | Controls & risks`; system status as a tile grid.
- Role-restricted pages: show `locked_card` instead of an error when the signed-in role lacks access (backend checks stay as they are).

## 9. Fonts

Put `Inter-Regular.woff2`, `Inter-Medium.woff2`, `Inter-SemiBold.woff2`, `Inter-Bold.woff2` in `static/fonts/` (official Inter release, OFL licence; add a short `static/fonts/README.md` with the licence note). Enable them with `[[theme.fontFaces]]` in `.streamlit/config.toml` and set `font = "Inter"`. If the files are missing, keep the system fallback stack and tell the user exactly where to put them; the layout must not break either way.

## 10. Streamlit 1.66 technical notes

- `st.container(key="x")` adds the CSS class `st-key-x`: use it for the navbar, cards and any fixed element. Prefer keys over fragile auto-generated class names.
- `data-testid` names can differ between Streamlit versions: inspect the rendered DOM (browser devtools or a Playwright dump) before writing selectors for the header, sidebar, tabs and main container; do not guess.
- Keep `st.navigation(position="hidden")` and the hand-rendered sidebar links, but render them grouped with Material icons and active/locked states.
- Inject the stylesheet on every run (a test checks it). Raise the stylesheet line budget in `tests/test_design.py` deliberately (about 500 lines) and keep the other design assertions (wrapping KPI values, header alignment) or update them to the new class names in the same commit.
- Hex colour literals are allowed only in `styles.css`, `charts.py` and `.streamlit/config.toml` (a test scans `main.py` and `pages/*.py`). Inline SVG must use CSS variables or `currentColor`.
- Pages are also loaded directly by `AppTest.from_file(page)` in tests; each page must keep working standalone for a signed-in session and keep stopping safely when no user is present.
- Never run a gated page's code for a signed-out visitor.

## 11. Verification (every phase)

1. `pytest -q`, `ruff check .`, `python run.py check`, `python scripts/check_secrets.py`, all green. If a test breaks because of an intentional UI change, update it in the same commit and say which and why. Never delete a test just to make it pass.
2. Visual check. Use any headless browser available (Playwright if installable, otherwise Edge/Chrome headless) to take screenshots at **1440x900, 1920x1080 and 1280x720** of every page touched, signed out and signed in (Owner and Viewer), with the "Stable and healthy" and "High expense, shortage" cases. Save to `evidence/ui/`. Open them and fix anything clipped, overlapping, misaligned, or off-scale. If no browser can be launched, say so plainly and list what you could not verify; never claim a visual result you did not see.
3. Report real results only (CLAUDE.md rule 10).

## 12. Acceptance checklist (the redesign is done when all are true)

- [ ] No page content is clipped at the top; title is fully visible at 1280, 1440, 1920 widths.
- [ ] Fixed navbar with logo, project name, Sign in / user menu + Log out on every screen.
- [ ] Fixed, non-collapsible, grouped sidebar with Material icons, active state, locked state for signed-out/unauthorised.
- [ ] One font family, one type scale; KPI values identical size across cards; nothing visibly too large or too small.
- [ ] Palette is green + off-white only (plus amber accent and status colours); charts follow the sample style; four-layer meanings unchanged.
- [ ] Business/Scenario selectors appear once per page, in the page header.
- [ ] Public Overview: hero with business-themed background, tagline, 5 feature buttons, questions, flow, role cards with demo sign-in, trust strip; readable without login; gated pages ask to sign in and return after login.
- [ ] Every signed-in page uses cards on a grid; no page needs more than ~2 screens of scrolling for its main content; long forms are in tabs/expanders.
- [ ] Sign-in screen redesigned; demo role buttons and password login both work; errors friendly.
- [ ] `docs/DESIGN.md` updated to point to this spec (tokens, layout, chart rules), `docs/PROGRESS.md` updated, screenshots in `evidence/ui/`.
