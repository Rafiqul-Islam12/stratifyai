# Execution Evidence Index

Each line identifies an existing evidence artifact and the claim it supports. Artifacts use synthetic data and are not production validation.

- `evidence/test_results.txt` — recorded full pytest run: 197 passed, exit code 0, 2026-10-18.
- `evidence/task_suite_results.md` — 13/13 scripted service workflows passed, with per-workflow details.
- `evidence/security_eval.md` — 60 role/action decisions, 10 poisoned-name cases, grounded receipts and audit tamper detection.
- `evidence/backtest_results.csv` — per-case model and naive-baseline training/holdout counts, MAE and WAPE.
- `evidence/backtest_results.md` — readable holdout method, per-case metrics and explicit accuracy caveat.
- `evidence/decision_quality.json` — selected plan, deterministic minimum balance, reserve status and simulated breach probability for five cases.
- `evidence/t02-overview-review.png` — historical Overview browser capture from T02; retained only as an older design record.
- `docs/img/overview.png` — current 1440px public Overview capture of the green UI, used by the README.
- Runtime simulated-action log — `evidence/sandbox_log.jsonl` is the default destination; no such file is currently checked in. The service records `network_sent: false` when an owner simulates an approved draft. Do not describe the log as existing until a live demo creates it.

Fresh 1440px screenshots still requested for the signed-in current UI: `docs/img/cashflow.png`, `docs/img/lab.png`, `docs/img/financing.png`, `docs/img/analysis.png`, `docs/img/copilot.png`, `docs/img/approvals.png`, `docs/img/upload.png`, and `docs/img/security.png`. The public Overview screenshot is already captured.