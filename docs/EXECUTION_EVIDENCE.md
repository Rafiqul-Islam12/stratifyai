# Execution Evidence Index

**Technical report:** [Technical_Documentation_StratifyAI_Final.docx](Technical_Documentation_StratifyAI_Final.docx) — complete formatted technical documentation (Times New Roman, 12 pt; reviewed 2026-10-20).

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

The requested signed-in UI evidence is now included in `docs/img/`: Overview Case 3, cash flow, Lab comparison and lever/stress states, financing/readiness, Case 2 analysis/watchlist, Copilot with expanded evidence receipt, draft-to-approval timeline, audit verification, formula-like upload validation, and the security permission matrix. Four paired exhibits combine directly captured states of the same workflow; the original captures are preserved alongside the composed report figures.