# CHECKLIST (coverage matrix). Status: [ ] open, [~] partial, [x] done with evidence (test or file).

## Master brief
- [ ] B-01 General SME copilot, not import-only (T03, T05, T08)
- [x] B-02 Lab Option 0 baseline (T07) — `core/lab.py`, `tests/test_lab.py`
- [x] B-03 Option A with three separate levers L1/L2/L3 (T07, T08) — isolated and combined plans in `core/lab.py`, controls in `app/pages/lab.py`
- [x] B-04 Option B partial financing (T07) — remaining gap after A, tested against C in `tests/test_lab.py`
- [x] B-05 Option C full financing (T07) — based on original gap with documented T06 rounding
- [x] B-06 Per-plan display: before/after balance, gap and shortage date, financing amount and cost, repayment capacity, risks, assumptions and sources, pros, cons, next steps (T07, T08) — `core/lab.py`, `app/pages/lab.py`
- [x] B-07 Hypothetical actions never assumed real (T07, T08, T12) — plan layers are labelled; T12 requires owner approval and simulated execution only (`services/agent_actions.py`)
- [~] B-08 Deterministic numbers; AI only explains (T07, T13) — Decision Lab engine is deterministic; copilot rules remain in T13
- [x] B-09 Lab answers the five key questions (T08) — structured answers rendered in `app/pages/lab.py`
- [x] B-10 Forecast 8-13 weeks, shortage date and amount, configurable reserve, actual vs forecast distinct (T05) — core/forecast.py and tests/test_forecast.py
- [x] B-11 Financing advisor: gap, capacity, templates, cost, schedule, risks, missing info, no approval claims (T06) — `app/pages/financing.py`, `core/financing.py`, `tests/test_financing.py`
- [x] B-12 Business analysis with reliable metrics only (T10) — `core/analysis.py`, `app/pages/analysis.py`, `tests/test_analysis.py`; unsupported indicators carry explicit reasons
- [ ] B-13 Grounded copilot, missing-data answers, untrusted input handling (T13)
- [x] B-14 Security: validation, backend RBAC, owner approval, audit, env secrets, safe errors (T04, T11, T12) — upload validation, backend role checks, owner-only approval, audit chain, env secrets and safe errors are implemented (`services/agent_actions.py`, `services/permissions.py`)
- [ ] B-15 No real payments, loans or bank claims (T12, T16)
- [x] B-16 Import demo scenario and stress tests (sales -20%, costs +15%, late payments, FX) editable (T08) — `core/stress.py`, `core/import_scenario.py`, and Lab controls
- [x] B-17 CSV/Excel upload and validation of dates, amounts, types, duplicates, missing values (T04) — tests in tests/test_validation.py
- [x] B-18 Synthetic data and illustrative terms labelled (T03, T06, T14) — Financing page banner and synthetic-case context; T14 cross-page review remains
- [~] B-19 Transparent formulas, no double counting, four layers separated (T05, T07, T14) — T05 actual and forecast are separate; matching invoice/bill categories are excluded from run rate; T07 tags simulated plans HYPOTHETICAL; cross-page layer review remains in T14
- [ ] B-20 No accuracy claim without backtest (T15)
- [x] B-21 Five synthetic cases (T03) — five generated case folders, schema validation and deterministic hash test in tests/test_data.py
- [ ] B-22 Required tests: gap, alerts, scenarios, financing cost, invalid data, unauthorized actions, audit tamper, AI grounding (T15)
- [ ] B-23 UI/UX direction followed (T02, T14)
- [ ] B-24 End-to-end workflow works (T14, T18)
- [ ] B-25 Title and tagline correct everywhere (T02, T16)

## Seven additions
- [x] A-01 Agent action drafts with owner approval (T12) — persistent draft state machine and owner review tested in `tests/test_agent_actions.py`
- [~] A-02 Security tiers, hash-chained audit and known-risk list are displayed in T11; self-assessment report is T16
- [ ] A-03 Backtest vs naive baseline (T15)
- [x] A-04 P10/P50/P90 band and computed shortage probabilities (T09) — `core/montecarlo.py`, Cash Flow and Lab uncertainty displays, `tests/test_montecarlo.py`
- [x] A-05 Deterministic best-plan rule, Option 0, separate levers (T07) — `core/lab.py`, `tests/test_lab.py`
- [x] A-06 Financing templates and repayment-capacity formula (T06) — `core/financing.py`, `tests/test_financing.py`
- [ ] A-07 Deliverables and schedule (T16, T18)

## UI requests
- [ ] U-01 Clean top-level UI (T02, T14)
- [~] U-02 Dynamic features: sliders, instant recalculation, click-through (T08, T14) — Lab sliders recalculate immediately; cross-page navigation polish remains in T14
- [~] U-03 Beautiful charts (T05, T08, T09, T10) — Cash Flow actual/forecast and P10-P90 band; later chart pages remain
- [ ] U-04 Colour grading and layer colours (T02)
- [ ] U-05 Font and typography (T02)
- [ ] U-06 Alignment and spacing (T02, T14, T18)
- [ ] U-07 Overview shows all key details (T14)
- [ ] U-08 Sidebar, header, footer, navigation (T02)
- [ ] U-09 Loading, empty and error states (T02, T14)
- [~] U-10 Load demo business button (T04, T14) — Data Upload loads all five cases; Overview entry point remains in T14
- [ ] U-11 Decision report download (T15)
- [ ] U-12 English UI (all)

## Competition
- [ ] C-01 Technical documentation (T16)
- [ ] C-02 Deck outline for max 10 minutes (T16)
- [ ] C-03 Demo script for max 5 minutes (T16)
- [~] C-04 Source, README, deployment instructions, tests, GitHub (T01, T16, T18) — source, README stub and tests done (T01); deployment instructions are T17, no GitHub remote yet
- [ ] C-05 Security self-assessment (T16)
- [~] C-06 Execution evidence logs (T12, T15) — T12 sandbox execution and audit events are logged; consolidated evaluation evidence remains in T15
- [ ] C-07 Integrity: no copied code, licences respected (T18)
- [ ] C-08 English everywhere (all)

## Workflow
- [ ] W-01 Token discipline followed (all)
- [ ] W-02 Handoff files kept current (all)
- [ ] W-03 One task per turn, stop and check (all)

## Added differentiators (our own designs)
- [x] D-01 System status panel on the Security page (T11) — version, synthetic data mode, copilot mode, audit chain, test evidence, and local fonts status
- [ ] D-02 Copilot Receipt per answer (T13)
- [ ] D-03 Receivables watchlist (T10)
- [ ] D-04 Verifiable readiness pack with hash check (T10)
- [ ] D-05 Scripted task-completion suite with results (T15)
- [ ] D-06 STRIDE threat model and LLM-risk mapping in docs (T16)
- [~] D-07 CI workflow runs tests on every push (T01) — .github/workflows/ci.yml on push+PR, Python 3.11 and 3.12, `pytest -q` then `ruff check .`; both commands pass locally, CI has not yet run remotely (no origin)
- [x] D-08 One-command launcher run.py (T01, T17) — setup/start/demo/test/eval/check/status/report; verified setup, test, check, status and a live HTTP 200 from `start`
- [ ] D-09 Consolidated final report builder (T15)

## Packaging and reachability
- [ ] P-01 Docker image runs the app offline (T17)
- [ ] P-02 Submission zip built by script, excludes secrets (T17)
- [ ] P-03 Demo video MP4 included inside the submission package, not only a link (T17, T18)
- [ ] P-04 No CDN or external fonts; works offline and on mainland China networks (T02, T17, T18)
- [ ] P-05 Optional live demo link, labelled as possibly unreachable in mainland China (T17)
- [ ] P-06 GitHub README follows docs/README_BLUEPRINT.md and the repo is public before submission (T16, T18)

