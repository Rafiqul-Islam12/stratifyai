# StratifyAI evaluation report

Generated: 2026-10-18T06:59:41+00:00

## Scope and caveat

This report uses synthetic case data only. Forecast and decision-quality metrics are an offline evaluation, not a claim of live or production accuracy. Financing terms and scenario changes are illustrative and hypothetical.

## Backtest against naive baseline

# Cash-flow backtest

Holdout is the last 8 recorded weeks, or the last 25% of history when that is longer. Forecasts use records issued by the cutoff only. MAE is BDT/week; WAPE is a ratio. All data are synthetic and these results are not a claim of production accuracy.

## stable_healthy

| Method | MAE (BDT/week) | WAPE |
|---|---:|---:|
| StratifyAI forecast | 255,370.86 | 330.99% |
| Naive last-4-week mean net flow | 32,631.25 | 42.29% |

Holdout: 10 weeks; training cutoff: 2026-05-04. The deterministic forecast had higher MAE than this naive baseline on this holdout; this small synthetic result is reported as observed and is not evidence of improved accuracy.

## sales_drop_cost_rise

| Method | MAE (BDT/week) | WAPE |
|---|---:|---:|
| StratifyAI forecast | 166,949.39 | 231.37% |
| Naive last-4-week mean net flow | 140,806.33 | 195.14% |

Holdout: 10 weeks; training cutoff: 2026-05-04. The deterministic forecast had higher MAE than this naive baseline on this holdout; this small synthetic result is reported as observed and is not evidence of improved accuracy.

## high_expense_shortage

| Method | MAE (BDT/week) | WAPE |
|---|---:|---:|
| StratifyAI forecast | 256,412.36 | 374.69% |
| Naive last-4-week mean net flow | 26,176.58 | 38.25% |

Holdout: 10 weeks; training cutoff: 2026-05-04. The deterministic forecast had higher MAE than this naive baseline on this holdout; this small synthetic result is reported as observed and is not evidence of improved accuracy.

## delayed_customer_payments

| Method | MAE (BDT/week) | WAPE |
|---|---:|---:|
| StratifyAI forecast | 297,374.47 | 989.17% |
| Naive last-4-week mean net flow | 18,340.14 | 61.01% |

Holdout: 10 weeks; training cutoff: 2026-05-04. The deterministic forecast had higher MAE than this naive baseline on this holdout; this small synthetic result is reported as observed and is not evidence of improved accuracy.

## import_financing

| Method | MAE (BDT/week) | WAPE |
|---|---:|---:|
| StratifyAI forecast | 299,112.58 | 576.99% |
| Naive last-4-week mean net flow | 23,607.15 | 45.54% |

Holdout: 10 weeks; training cutoff: 2026-05-04. The deterministic forecast had higher MAE than this naive baseline on this holdout; this small synthetic result is reported as observed and is not evidence of improved accuracy.


## Decision quality

- stable_healthy: Option 0; reserve maintained: True; minimum BDT 3,246,586.55 vs reserve BDT 389,265.83; breach probability 0.00%.
- sales_drop_cost_rise: Option 0; reserve maintained: False; minimum BDT -1,594,784.34 vs reserve BDT 529,253.62; breach probability 100.00%.
- high_expense_shortage: Option A; reserve maintained: False; minimum BDT -6,229,560.42 vs reserve BDT 622,695.93; breach probability 100.00%.
- delayed_customer_payments: Option 0; reserve maintained: False; minimum BDT -188,551.13 vs reserve BDT 452,785.87; breach probability 100.00%.
- import_financing: Option A; reserve maintained: False; minimum BDT 253,078.71 vs reserve BDT 420,886.89; breach probability 98.45%.

Reserve check passed for 1/5 cases. In the other 4 case(s), no candidate maintained reserve through the horizon; the Lab's documented rule selects the smallest-gap plan and reports its computed breach probability. These outcomes are not hidden as successful recommendations.

## Security evaluation

# Security evaluation

Evaluated: 2026-10-18T06:57:57+00:00

- Authorization matrix: PASS (60 role/action decisions; all matched registry).
- Injection and grounding: PASS (10/10 poisoned-name cases excluded; grounded answers validated with 10 evidence receipts).
- Audit tamper detection: PASS (tamper detected at entry 1).


## Scripted task suite

# Scripted task-completion suite

Evaluated: 2026-10-18T06:59:41+00:00

Overall: 13/13 passed (100.0%).

| ID | Case | Steps | Expected result | Result | Detail |
|---|---|---|---|---|---|
| T01 | high_expense_shortage | load validated case; run deterministic forecast | reserve shortage is detected with a real forecast week | PASS | expected outcome observed |
| T02 | high_expense_shortage | load validated case; run Decision Lab | baseline, isolated levers, combined and financing plans are available | PASS | expected outcome observed |
| T03 | stable_healthy | load validated case; run Decision Lab; select rule-based recommendation | recommended plan is feasible under recomputed deterministic balances | PASS | expected outcome observed |
| T04 | import_financing | load validated case; apply explicit stress inputs; run forecast | stress result is distinct and finite; source case remains unchanged | PASS | expected outcome observed |
| T05 | high_expense_shortage | load validated case; compute baseline gap; run illustrative financing calculation | financing amount, cost and repayment schedule are computed | PASS | expected outcome observed |
| T06 | delayed_customer_payments | authenticate finance_ops; create a collection reminder draft | draft remains a local draft and identifies manual review only | PASS | expected outcome observed |
| T07 | delayed_customer_payments | authenticate finance_ops; create reminder; submit draft; authenticate owner; approve draft | only owner advances submitted draft to approved | PASS | expected outcome observed |
| T08 | stable_healthy | authenticate viewer; request lab.run permission | viewer is denied and denial is audited | PASS | expected outcome observed |
| T09 | stable_healthy | validate upload containing a formula-like cell | formula cell is neutralized and reported | PASS | expected outcome observed |
| T10 | stable_healthy | authenticate owner; append audit event; verify audit chain | untampered audit chain verifies | PASS | expected outcome observed |
| T11 | stable_healthy | append audit event; tamper with persisted row after disabling guard trigger; verify audit chain | hash-chain verifier detects tampering | PASS | expected outcome observed |
| T12 | high_expense_shortage | authenticate owner; ask grounded funding question; validate citations and numbers | answer passes evidence and numeric grounding validation | PASS | expected outcome observed |
| T13 | delayed_customer_payments | load case; compute business analysis | analysis snapshot contains finite computed values and explicit unavailable reasons | PASS | expected outcome observed |


## Test suite

Recorded pytest exit code: 0

```text
StratifyAI full test run
Timestamp (UTC): 2026-10-18T06:57:57+00:00
Command: python -m pytest -q
Exit code: 0

--- stdout ---
........................................................................ [ 36%]
........................................................................ [ 73%]
.....................................................                    [100%]
197 passed in 43.10s

--- stderr ---

```

## Checklist status

Tasks complete: 15/18 (83.3%)
Coverage checklist: 41 done, 5 partial, 24 open of 70 items.

## Evidence files

- `evidence/backtest_results.csv` and `.md`
- `evidence/decision_quality.json`
- `evidence/security_eval.md`
- `evidence/task_suite_results.md`
- `evidence/test_results.txt`

## Limitations

The backtest is based on a small synthetic holdout set; results may be poor and should be read alongside the naive baseline. The decision-quality check recomputes the selected Lab plan using the same deterministic engines and reports the seeded uncertainty estimate. No result implies a lender decision, customer payment, supplier agreement, or real-world execution.
