# BRIEF (condensed master brief)

## Product
AI-powered SME Finance Copilot for small and medium business owners: understand financial position, anticipate cash shortages, evaluate financing need, make better decisions. It stays a GENERAL SME copilot (not import-only). It supports decisions; it never makes unsupported guarantees or executes consequential actions automatically.

The product must answer:
1. When and why might the business run short of cash?
2. How much funding might be required?
3. Can the shortage be reduced without borrowing?
4. If financing is needed, which options are worth comparing?
5. What happens if sales fall, costs rise or payments are delayed?

## Flagship: Liquidity Decision Lab
When a shortage is detected, compare:
- **Option 0, Do nothing (baseline).**
- **Option A, Collect and Optimize:** three SEPARATE levers shown individually and combined: (L1) follow up overdue receivables, (L2) reschedule eligible supplier payments, (L3) reduce discretionary expenses.
- **Option B, Partial Financing:** finance only the gap remaining after Option A.
- **Option C, Full Financing:** finance the original gap.
For each plan display: projected cash balance before/after, funding gap and shortage date, financing amount and cost, repayment capacity and key risks, assumptions and data sources, advantages, disadvantages, recommended next steps.
Deterministic best-plan rule (see DECISIONS.md). AI explains only; it never invents numbers. Customer early payment, supplier acceptance and lender approval are HYPOTHETICAL until the owner confirms.

## Supporting features
- A. Cash-flow forecast and alerts: 8 to 13 weeks, shortage date and amount, configurable minimum reserve, actual vs forecast vs assumption clearly distinguished, P10/P50/P90 uncertainty band and shortage probability.
- B. Financing advisor: funding gap, repayment capacity, comparison of documented or explicitly hypothetical terms (generic templates), cost, repayment schedule, risks, missing information. Never guarantee approval; never invent lender eligibility rules.
- C. Business financial analysis: income, expenses, receivables, payables, cash, indicators, trends; show only metrics that can be computed reliably; otherwise "not available" with reason.
- D. Evidence-grounded copilot: answers from uploaded data, computed results and documented assumptions; explains why; states missing data and uncertainty; treats uploaded text as untrusted data.
- E. Security, permissions, audit: validate uploads and inputs; role-based access enforced in backend; owner approval before any consequential action; audit of decisions, scenario changes, approvals, actions; secrets in environment variables; safe error handling.
- F. Agent actions (drafts only): collection reminders, supplier deferral requests, financing application pack, plan proposals. Owner approves; execution is simulated and logged.

## Import demonstration scenario (optional, NOT a separate module)
Business imports goods from China or another supplier. Inputs: product cost, deposit %, shipping and other import costs, duties/taxes (editable assumption), FX rate, lead time, available cash, expected sales and collection timeline, existing obligations, financing terms. Stress tests (editable examples, not predictions): sales -20%, shipping/other costs +15%, customer payments later by N days, FX shock. Same core workflow must work for other SMEs. Currency BDT.

## Data and calculation principles
CSV (and Excel where practical) upload. Validate dates, amounts, transaction types, duplicates, missing values. Synthetic sample data, clearly labelled; illustrative financing terms labelled. Transparent formulas. Prevent double counting. Separate ACTUAL, FORECAST, HYPOTHETICAL, CONFIRMED. Never claim forecast accuracy without evaluating against known outcomes (backtest vs naive baseline).

## Evaluation
Five synthetic SME cases: (1) stable with enough cash, (2) delayed customer payments, (3) high expenses and upcoming shortage, (4) import financing, (5) lower sales or higher costs. Tests: funding gap, shortage alert logic, scenario comparison, financing cost and repayment, missing or invalid data, unauthorized actions blocked, audit tamper detection, AI grounding. Report real results only.

## Security tiers
READ, DRAFT, APPROVAL_REQUIRED (owner), MONEY_MOVEMENT (never executed by the system, for any role). Hash-chained audit log. Known-risk list and security self-assessment report.

## UI direction
Clean, modern, professional dashboard: sidebar, header, footer, consistent colours and typography, KPI cards, readable tables, visible assumptions, few meaningful charts, no decorative AI. Priority order: business health, forecast and alerts, Liquidity Decision Lab, financing, AI explanations. The Lab must be immediately noticeable in a short demo.

## Final success criteria
One complete workflow: Business data, Cash-flow forecast, Shortage detected, Liquidity Decision Lab, Financing comparison, Evidence-backed recommendation, Owner decision and audit history. Transparent, secure within prototype scope, clearly differentiated by the Lab.

## Added differentiators (our own designs; never copy another team's code or text)
- System status panel on the Security page (version, data mode, copilot mode, audit chain status, last test run, fonts local).
- Copilot Receipt per answer: mode, evidence IDs used, masked-field count, whether any external call was made, validator result.
- Receivables watchlist with explainable score linked to invoice evidence.
- Verifiable Readiness Pack: exportable summary with SHA-256 hash, consent flag and expiry, plus a verify tool (integrity check only, not a lender submission).
- Scripted task-completion suite with pass/fail evidence (proof for the 40% criterion).
- STRIDE threat model and LLM-risk mapping in the security documents.
- CI that runs tests on every push; one-command launcher `python run.py`.
- Consolidated final report builder that compiles real evidence.

## Competition deliverables (International Track)
Technical documentation (architecture, core algorithms, security design); presentation deck (max 10 minutes); demo video (optional, max 5 minutes); source code with README, GitHub link, deployment instructions and test cases; security self-assessment (permission-tier implementation and known-risk list); execution evidence (simulated-account/sandbox operation logs and demo video). Entries must be independent work, free of plagiarism; third-party code properly licensed. Submission deadline 20 Oct 2026, 23:59 Beijing time.
