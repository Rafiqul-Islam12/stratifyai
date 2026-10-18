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
