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
