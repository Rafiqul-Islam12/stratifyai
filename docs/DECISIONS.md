# DECISIONS (formulas, defaults, assumptions). Defaults are editable and labelled in the UI.

## General
- Weekly buckets (week starts Monday). Horizon 13 weeks (minimum 8 if data is short). Currency BDT.
- ACTUAL = recorded transactions; FORECAST = engine output from actual data and default assumptions; HYPOTHETICAL = what-if changes; CONFIRMED = hypothetical changes the owner approved (owner-asserted, not independently verified).

## Forecast
- Opening cash = latest actual balance.
- Receivable expected week = due date + customer typical delay (median historical delay if at least 3 paid invoices, else 0 days; editable).
- Payables due on their due date. Recurring expenses and run-rate sales = average weekly amount by category over the last 8 weeks, ONLY for categories with no invoice/bill records (this is the no-double-counting rule; invoices/bills are never also in run-rate).
- Minimum reserve is configurable (default = 2 weeks of average fixed outflows).
- Shortage week = first week with closing balance below reserve (also flag below zero separately). Funding gap = max(0, reserve - minimum closing balance in horizon) plus optional buffer % (default 0).

## Decision Lab levers (all HYPOTHETICAL)
- L1 Collections: collect x% (default 50) of overdue receivables within y weeks (default 2), with haircut z% (default 0). Collected receivables are removed from their later expected week (no double counting).
- L2 Reschedule: defer payables flagged deferrable by n weeks (default 2); deferred amounts are moved (not deleted) to the later week, which may fall beyond the horizon; optional late fee % (default 0); flag relationship risk.
- L3 Expense reduction: reduce discretionary categories by x% (default 10) from week w (default 1).
- Each lever is evaluated in isolation and combined.
- Option B finances only the remaining gap after Option A (0 means no financing needed). Option C finances the original gap.

## Financing templates (ILLUSTRATIVE, not real lender terms; label in UI)
- Term loan: 14% p.a., 1% fee, 6 months, equal monthly instalments (annuity).
- Invoice financing: 80% advance, 2.0% fee per 30 days outstanding.
- Supplier credit: +30 days, cost 1.5% of invoice value.
- Credit line: 16% p.a. on drawn amount, 0.5% commitment fee.
- Total cost = interest + fees + explicit hypothetical costs (e.g. late fees).
- Repayment capacity ratio = (average weekly net operating cash flow before debt service x weeks per period) / debt service per period. Labels: >= 1.25 comfortable, 1.0 to 1.25 tight, < 1.0 stressed (rules of thumb, editable, not lender rules).

## Best-plan rule (deterministic)
Candidates: Option 0, A, B, C. Feasible = projected minimum balance >= reserve on the P50 (deterministic) path; also report breach probability from the uncertainty model. Choose the feasible plan with the lowest total cost; ties broken by lower repayment pressure, then fewer unconfirmed assumptions. If none is feasible, say "no plan fully closes the gap" and recommend the plan with the smallest remaining gap. Also output "Is borrowing necessary?" with the reason.

## Uncertainty
Monte Carlo, 2000 runs, fixed seed 42. Per-customer payment delay sampled from the empirical distribution (if at least 5 observations) else normal around the default delay with editable sd; sales variability coefficient editable. Outputs P10/P50/P90 closing balance per week and probability of falling below reserve and below zero. Every probability shown in the UI is computed, never hard-coded.

## Backtest
Hold out the last 8 weeks (or last 25% of history), forecast from earlier data, compare with a naive baseline (average net cash flow of the last 4 weeks). Metrics: MAE and WAPE. Report real numbers with the synthetic-data caveat.

## Financing readiness (indicator only, not an approval prediction)
Components (weights editable): repayment capacity 35, cash buffer 25, receivable quality 20, data completeness 10, trend 10. Output score 0 to 100 with reasons and a list of missing information.

## Receivables watchlist (our own formula, explainable)
Score 0 to 100 per customer, weights editable: overdue-amount share of the customer's open balance 40; weighted days overdue 30 (capped at 90 days); payment-delay trend 20 (recent delay versus earlier delay); concentration (customer share of total receivables) 10. Labels: below 30 normal, 30 to 60 watch, above 60 urgent (editable). Every score lists the invoice ids behind it.

## Runtime and distribution
- One launcher: `python run.py` (setup, demo, start, test, eval, check, status, report).
- Copilot llm mode (optional) uses a generic OpenAI-compatible endpoint from env (COPILOT_BASE_URL, COPILOT_MODEL, COPILOT_API_KEY); default is offline.
- No CDN or external fonts. Docker image runs offline. Live hosting (optional) is a bonus link and may be unreachable from mainland China; the demo video file is part of the submission package.

## Tooling (T01)
- Dependencies are pinned exactly in requirements.txt (recorded from `pip freeze` after `python run.py setup`) rather than left at the ">=" floors in the task spec, so a clean clone installs the same streamlit 1.66.0 the local demo was verified against.
- pytest.ini sets `testpaths = tests`. Without it, `pytest -q` at the repo root walks .venv and collects the installed packages' own suites (observed 4464 collected instead of 9). Keep the config while the venv stays inside the repo.
- scripts/check_secrets.py skips docs/inputs/ plus build and cache dirs, so the competition brief PDF is not scanned as project code. All tracked files and untracked non-ignored files are still scanned; it reported "no matches in 58 files".

