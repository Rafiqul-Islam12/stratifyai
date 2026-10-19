# Presentation Deck Outline

**Target:** 12 slides, 9 minutes 40 seconds total, within the 10-minute presentation limit. Every screenshot below is a capture request for the current UI at 1440px width. The existing `evidence/t02-overview-review.png` is an older shell and should not be reused as a current screenshot.

| # | Time | Slide and talking points | Screenshot to capture |
| ---: | ---: | --- | --- |
| 1 | 0:30 | **StratifyAI** — The Liquidity Decision Lab for SME Financial Intelligence. Topic E, synthetic-data prototype; no real integrations. | `docs/img/overview.png` |
| 2 | 0:40 | **Why now?** An SME can learn about a cash shortage too late; show how dated bills, receivables and transactions create a forward cash view. | `docs/img/cashflow.png` |
| 3 | 0:45 | **What runs where?** Uploaded data is validated; deterministic core computes; services authorize; Streamlit presents. Offline by default. | `docs/img/upload.png` |
| 4 | 0:55 | **See the shortage** — ACTUAL and FORECAST are distinct; reserve and first shortage week are explicit. | `docs/img/cashflow.png` |
| 5 | 0:45 | **See uncertainty** — P10/P50/P90 and breach probabilities are computed from seeded simulations, not hard-coded. | `docs/img/overview.png` |
| 6 | 1:10 | **Compare plans** — Option 0, L1 collections, L2 rescheduling, L3 spend reduction, then A/B/C; all changes are HYPOTHETICAL. | `docs/img/lab.png` |
| 7 | 0:45 | **Financing is illustrative** — compare schedule, cost and capacity indicator; make no lender approval claim. | `docs/img/financing.png` |
| 8 | 0:45 | **Business health** — analysis, aging, readiness and missing-data reasons. Readiness is not an approval score. | `docs/img/analysis.png` |
| 9 | 0:55 | **Copilot with evidence** — offline answer, masked evidence, cited numbers and receipt; show one unsupported/injection-style request rejected. | `docs/img/copilot.png` |
| 10 | 1:00 | **Human control** — finance_ops creates a draft; owner approves; app records local simulation only. | `docs/img/approvals.png` |
| 11 | 0:50 | **Security boundaries** — roles, tiers, audit hash chain and always-denied money movement; describe residual local-host risks. | `docs/img/security.png` |
| 12 | 0:40 | **Evidence and limitations** — 197 tests, 13/13 service workflows, 60 authorization decisions; model MAE beat by naive baseline in 0/5 cases. Close with next validation steps. | `docs/img/overview.png` |

**Total: 9:40.** Do not omit the poor backtest result or imply production forecasting accuracy. Detailed numbers are in `evidence/backtest_results.md` and `evidence/decision_quality.json`.