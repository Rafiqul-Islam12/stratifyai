# PROGRESS

Current task: T14 (awaiting user `next`)
Last updated: 2026-10-18

## In progress (checkpoints; one line per finished sub-step, cleared when the task is done)
- T14 checkpoint: computed Overview, five-case demo selector, hero forecast/uncertainty chart, plan/readiness/aging/approvals/audit panels and shared business/scenario/role header added; Overview, page smoke and security tests pass (21 tests), focused Ruff passes.
- T14 checkpoint: shared no-data states and direct-page permission guards added; AppTest matrix covers all 10 pages, five cases and four roles plus empty-state runs; 67 focused page/Overview/security tests pass, focused Ruff passes.
- T14 checkpoint: existing approval-to-Lab integration flow now loads its selected synthetic business through Overview before use; the formerly failing integration test passes.

## Done
- **T01 Scaffold, tooling, run.py launcher, CI, status script** (2026-10-17)
  - Folder skeleton: core/, services/, app/pages/, data/, tests/, scripts/, evidence/, static/fonts/, docs/img/, .streamlit/, .github/workflows/
  - `run.py` launcher (stdlib only): setup, start, demo, test, eval, check, status, report
  - `requirements.txt` + `requirements-dev.txt` pinned: streamlit 1.66.0, pandas 3.0.6, numpy 2.4.6, plotly 7.1.0, pydantic 2.14.1, pytest 9.1.1, openpyxl 3.1.5, ruff 0.17.1
  - `scripts/status.py`, `scripts/check_secrets.py`, `.env.example`, `.github/workflows/ci.yml` (Python 3.11 + 3.12)
  - `app/main.py` minimal scaffold page, `tests/test_smoke.py` (9 tests), `README.md` stub
  - Verified: `setup`, `test` (9 passed), `check` (exit 0), `status`, `start` serves on 127.0.0.1:8501 (Health: ok)
- **T02 Design system and app shell** (2026-10-17)
  - App shell, theme, shared components and charts are implemented in commit `9f1387a`.
  - Per the user's direction, font sizing, alignment, vertical text placement, and card text/layout are deferred to T14 cross-page polish.
- **T03 Synthetic data and schema** (2026-10-18)
  - Added typed Pydantic schemas and a loader for transactions, receivables, payables, profiles and assumptions.
  - Added a fixed-seed generator for five synthetic cases, with 39 weeks of transaction history, 10 synthetic customers, 6 synthetic suppliers and labelled case folders.
  - Generated all five cases; validated each case through the typed loader and confirmed repeat generation produces identical hashes.
  - Verified: `pytest -q` (33 passed), `python scripts/check_secrets.py` (no matches in 109 files); focused data tests (7 passed).
  - Local checkpoint commit: `10c8c6c`.
- **T04 Upload, validation and Data Upload page** (2026-10-18)
  - Added CSV/XLSX validation with 5 MB and 50,000-row limits, required columns, dates, amounts, transaction types, duplicate detection, currency consistency, text limits, and formula neutralisation.
  - Added row-level reports, preview, downloadable templates, validated session storage, and a selector that loads all five demo cases.
  - Verified good, missing-column and formula-cell uploads plus all five UI demo selections with Streamlit AppTest.
  - Verified: `pytest -q` (53 passed), `ruff check .` (all checks passed), `python scripts/check_secrets.py` (no matches).
  - Local checkpoint commits: `0b3e4d3`, `0417333`.
- **T05 Forecast engine, shortage alerts and Cash Flow page** (2026-10-18)
  - Added deterministic 13-week cash projections with actual history, unpaid receivables by expected date, unpaid bills by due date, last-eight-week category run rates and reserve/funding-gap summaries.
  - Added first reserve-breach and below-zero weeks with none/watch/critical severity; added Cash Flow chart, weekly table, assumptions and interactive reserve input.
  - Adjusted the delayed-customer synthetic case so its expected shortage outcome appears in the forecast (week 6 under defaults).
  - Verified all five qualitative case expectations and the Cash Flow page for all five cases with AppTest.
  - Verified: `pytest -q` (65 passed), `ruff check .` (all checks passed).
  - Local checkpoint commits: `c542e2b`, `610e827`.
- **T06 Financing module and Financing page** (2026-10-18)
  - Added four editable illustrative templates, validated terms, monthly schedules, annuity calculations, costs, capacity labels, deterministic risks and missing-information notes; the funding-gap rounding and repayment assumptions are documented in DECISIONS.md.
  - Built the interactive Financing page with case selection, editable rates/fees/tenor, schedule, cost chart, capacity summary and the required illustrative-terms banner.
  - Verified hand-calculated 100,000 BDT annuity, zero rate/gap, invalid terms, all template calculations and case 3 page recalculation using AppTest.
  - Verified: `pytest -q` (76 passed), `ruff check .` (all checks passed), secret scan (no matches in 115 files).
  - Local checkpoint commit: `c38831e`.
- **T07 Decision Lab engine** (2026-10-18)
  - Added deterministic Option 0, isolated L1/L2/L3, combined Option A and financing Options B/C with repayment schedule, cost, capacity, risks, assumptions/sources, plan explanations and five structured answers.
  - Added a hand-built known-number mini scenario covering no-double-counted collections, combined-lever impact, best-plan/no-feasible selection, B/C facility comparison, serialization, determinism and hypothetical layer tags.
  - The case 3 comparison confirms Option C uses the rounded original gap (BDT 6,890,000 for a BDT 6,889,777 gap), Option B is smaller, and prints the best-plan reason.
  - Verified: `pytest -q` (87 passed), `ruff check .` (all checks passed), `scripts/show_lab.py` (case 3 output and Option B/C facility assertions passed), secret scan (no matches in 118 files).
  - Local checkpoint commit: `4a8c54a`.
- **T08 Decision Lab page, Assumptions, stress and import scenario** (2026-10-18)
  - Added deterministic sales, operating cost, customer-delay and import-linked FX stress inputs; built editable case 4 deposit, landed-cost and sales-collection events from user-entered assumptions.
  - Added a shared per-case session assumption store with validated ranges and reset; wired the Lab page with five answers, four plan cards, balance/cost/lever charts, stress and import controls, plan details, and up to three saved comparisons. Proposal saving remains disabled until the draft service is built.
  - Verified AppTest across all five cases; sales and lever slider recalculation; reserve changes; case 4 FX/deposit edits; assumption reset; and saving three scenarios.
  - Verified: `pytest -q` (105 passed), `ruff check .` (all checks passed), `scripts/show_lab.py` (case 3 comparison passed), secret scan (no matches in 123 files).
  - Local checkpoint commits: `5cabc5c`, `4d81140`.
- **T09 Uncertainty bands and shortage probability** (2026-10-18)
  - Added seeded NumPy Monte Carlo with 2,000 runs, customer-level delay sampling, editable sales receipt variability and delay standard deviation, weekly P10/P50/P90 balances, reserve/zero probabilities, and any-week reserve-breach probability.
  - Added cached Cash Flow uncertainty output and the adjustable P10-P90 band; alerts report computed reserve-breach probability. Lab reruns each plan's changed collection, payable, and financing flows and displays computed probabilities and weekly risk.
  - Verified: `pytest -q` (110 passed), `ruff check .` (all checks passed), `scripts/show_lab.py` (case 3 facility/best-plan smoke passed), secret scan (no matches in 125 files).
  - Local checkpoint commit: `e88c7f3`.
- **T10 Business Analysis, receivables watchlist, readiness indicator and pack** (2026-10-18)
  - Replaced placeholder Analysis UI with computed weekly/monthly income and expense summaries, aging, DSO/DPO when invoice data supports them, burn/runway, gross margin only with identified COGS, trend flags and an evidence-linked customer watchlist.
  - Added weighted readiness scoring with component reasons/missing data, editable weights, and a consent/expiry-marked Markdown pack with SHA-256 verification tool on Financing. Labels explicitly say the indicator is not loan approval and pack integrity is not lender submission.
  - Verified: `pytest -q` (117 passed, including all five Analysis and Financing cases), `ruff check .` (all checks passed), secret scan (no matches in 130 files).
  - Local checkpoint commit: `280a988`.
- **T11 Security core, roles, audit chain, Approvals/Audit and Security pages** (2026-10-18)
  - Added demo PBKDF2 authentication with server-issued session tokens, backend action tiers and role checks, and an always-denied MONEY_MOVEMENT action.
  - Added sanitized append-only SQLite audit events with hash-chain verification and update/delete triggers; wired login, denials, validated uploads, scenario changes, drafts, approvals, and simulated execution to authorized service entry points.
  - Added role-filtered app navigation, Approvals/Audit with filters and Verify chain, and Security controls, role matrix, and system status. The sign-in page retains username/password login and provides four labelled demo quick-sign-in buttons; the password-free shortcut is documented as demo-only. Sidebar links now use registered `st.Page` objects, fixing auditor navigation to Approvals.
  - Verified: `pytest -q` (126 passed, including role matrix, denial logging, role forgery, money movement denial, tamper detection, password login, all four demo buttons and auditor Approvals navigation), `ruff check .` (all checks passed), `run.py check` (health check passed), secret scan (no matches in 136 files).
- **T12 Agent action drafts, approval workflow, simulated execution** (2026-10-18)
  - Added persistent, idempotent drafts for collection reminders, supplier deferrals, financing packs and Lab proposals. finance_ops can create and view own drafts; only owner can approve/reject and simulate execution. Approvals includes payload previews, comments and status timeline; Lab proposals carry owner-confirmed assumptions into the chart layer.
  - Simulated execution is local-only, audited and appended to `evidence/sandbox_log.jsonl`; MONEY_MOVEMENT remains denied. Untrusted draft text is escaped in deterministic templates.
  - Verified: `pytest -q` (130 passed, including full UI approval/rejection/execution and Lab confirmation flow), `ruff check .` (all checks passed), `run.py check` (health passed), secret scan (no matches in 138 files).
  - Commit: `T12: agent drafts and approval workflow`.
- **T13 Grounded Copilot, injection protection, offline mode and receipt** (2026-10-18)
  - Added permission-checked evidence packs from the deterministic forecast, Decision Lab, analysis and readiness results, with active session assumptions and stable evidence IDs. Customer and supplier names and free-text source fields are excluded; entity IDs are sent instead.
  - Added deterministic routing for shortage, funding gap, plan comparison, a bounded read-only customer-delay what-if, data quality and readiness. Unsupported questions return a cited missing-data response.
  - Added offline-by-default template answers; optional generic OpenAI-compatible LLM mode sends only the question and masked evidence JSON, treats all supplied content as untrusted, validates citations and numeric values, and falls back offline on provider or validation errors.
  - Added 500-character query bound, hashed query audit events with the Copilot receipt, backend `copilot.ask` authorization, and no action execution path. The interactive page displays the answer receipt and evidence drawer under each response.
  - Verified: `pytest -q` (147 passed; 17 T13 tests), `ruff check .` (all checks passed), `python run.py check` (health passed; offline/no key), `python scripts/check_secrets.py` (no matches in 140 files).
  - Local checkpoint commits: `e836284`, `64845c1`, `5de9115`.

## How to run
```
python run.py setup     # create .venv, install pinned deps, seed .env
python run.py demo      # setup if needed, then start and open the browser
python run.py test      # pytest -q
python run.py status    # tasks done, current task, last commits, tests
python run.py check     # health: imports, data, fonts, copilot mode, audit chain, .env
python run.py eval      # not built yet (T15)
python run.py report    # not built yet (T15)
```
Streamlit page is `app/main.py`, served on `http://127.0.0.1:8501`.
Python 3.11.9 in `.venv`; no CDN and no external fonts.
Secret scan: `python scripts/check_secrets.py` (exit 0 = clean).

## Known issues
- T02 visual follow-up deferred at the user's direction: font sizing, alignment, vertical text placement, and card text/layout need review and correction during T14 cross-page UI polish. T02 shell is implemented; the user confirmed all 10 pages are clickable and show content, with these visual issues remaining.
- The competition PDF in docs/inputs/ could not be read on this machine (no poppler, no PDF library; the file has no /ToUnicode CMap). docs/COMPETITION.md is therefore unverified against the PDF - verify by hand before submission.
- `python run.py start` leaves the server running in its terminal (normal Streamlit behaviour); stop with Ctrl-C.
- `python run.py status` reports the passing test count but then errors in `scripts/status.py` because `result.stdout` is `None`.
- T08 import sales ramp uses recent actual weekly inflows as its deterministic proxy; shipment costs, duties/taxes and timings remain user-editable hypothetical assumptions.
- evidence/ holds only .gitkeep until related later tasks; static/fonts/ has no Inter files, so the system fallback stack is active.

## Decisions or assumptions changed (details in DECISIONS.md)
- Streamlit pinned to 1.66.0 rather than ">= 1.45" so the demo is reproducible (>= 1.45 was the stated floor for self-hosted fonts).
