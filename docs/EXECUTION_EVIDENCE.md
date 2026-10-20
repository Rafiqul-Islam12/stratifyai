# Execution Evidence Index

**Formatted report:** [Execution Evidence Report](Execution_Evidence_Report.docx) - follows the typography and green heading treatment used in the final Technical Documentation.

**Technical documentation:** [Technical_Documentation_StratifyAI.docx](Technical_Documentation_StratifyAI.docx) and [TECHNICAL_DOC.md](TECHNICAL_DOC.md).

**Scope:** Topic E is non-on-chain. Evidence is from synthetic data and a local simulated-account workflow; no blockchain transaction hashes apply. Recorded tests and screenshots do not constitute live production validation.

## Recorded execution artifacts

- evidence/test_results.txt - archived full pytest run: 197 passed, exit code 0, 2026-10-18.
- evidence/task_suite_results.md - 13/13 scripted service workflows passed, with per-workflow details.
- evidence/security_eval.md - 60 role/action decisions, 10 poisoned-name cases, grounded receipts and audit tamper detection.
- evidence/backtest_results.csv and evidence/backtest_results.md - synthetic holdout metrics; model MAE is higher than the naive baseline in all five cases.
- evidence/decision_quality.json - selected plans, minimum balances, reserve outcomes and seeded simulated breach probabilities for five synthetic cases.
- evidence/t02-overview-review.png - historical T02 Overview review image; not current UI evidence.

## Interface captures

Current public and signed-in synthetic-data screenshots are checked in under docs/img/. The formatted report embeds eight core views: cashflow.png, lab.png, financing.png, analysis.png, copilot.png, approvals-workflow.png, upload.png and security.png. Supporting captures include overview-owner-case3.png, lab-levers.png, lab-stress.png, lab-levers-stress.png, financing-readiness.png, analysis-watchlist.png, approvals.png, approvals-pending.png, audit-verify.png and overview.png. Screenshots document selected UI states; they are not a video or proof that an action executed during a live session.

## Sandbox log and demo video

- evidence/sandbox_log.jsonl is the configured default runtime log destination. The JSONL file is absent from this checkout, so no live sandbox execution record is claimed. The service is designed to write local simulated-action entries with network_sent=false; scripted tests cover the simulation flow.
- docs/DEMO_SCRIPT.md contains a recording script, not a recorded demo video. No demo video file is included in this checkout.
- There are no on-chain transactions for this non-on-chain topic; transaction hashes are not applicable.

All financial cases, values and accounts are synthetic. Results are limited to their recorded scope and do not establish production readiness, forecast accuracy or independent security validation.
