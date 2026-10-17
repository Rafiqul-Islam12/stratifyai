# SECURITY (design baseline, extended in T11 and T16)

## Permission tiers
- READ: view data, dashboards, results.
- DRAFT: create scenarios and agent action drafts.
- APPROVAL_REQUIRED: approve/reject drafts and plans; only owner. Execution is simulated and logged.
- MONEY_MOVEMENT: never executed by the system for any role (always denied, always audited).

## Roles
- owner: READ, DRAFT, APPROVAL_REQUIRED, manage users/assumptions
- finance_ops: READ, DRAFT, upload data, run Lab; cannot approve
- viewer: READ only
- auditor: READ plus view audit log and verify the audit chain

## Demo authentication (T11)
- Usernames are `owner`, `finance_ops`, `viewer`, and `auditor`; the role is resolved from the server-side user record.
- The local synthetic-data demo defaults are `DEMO-owner-123`, `DEMO-finance-123`, `DEMO-viewer-123`, and `DEMO-auditor-123`. Replace them with `DEMO_OWNER_PASSWORD`, `DEMO_FINANCE_OPS_PASSWORD`, `DEMO_VIEWER_PASSWORD`, and `DEMO_AUDITOR_PASSWORD` in the ignored `.env` file for a local run.
- Passwords are held as salted PBKDF2-HMAC-SHA256 hashes in process memory. This is a demo authentication boundary, not a production identity provider.
- The sign-in page also exposes password-free quick-sign-in buttons for these synthetic demo accounts. This is a deliberate demo convenience and must be disabled before any production use.
- The SQLite audit database is `data/audit.sqlite3` by default; set `STRATIFY_AUDIT_DB` to select a different local path. Rows are sanitized, append-only under SQLite triggers, and linked by SHA-256 hashes.

## Controls (baseline)
Backend authorize() on privileged service calls; hash-chained append-only audit log with verify function; upload validation including spreadsheet formula-injection sanitising; untrusted-text handling for copilot; secrets only in .env; safe error messages; no real integrations. Pure parsing and deterministic calculation helpers do not mutate protected state.

## Known risks (initial list; keep honest and extend)
Demo authentication only (no MFA, seeded demo accounts); SQLite file is inside the trust boundary (a database administrator can edit it; chain makes edits detectable, not impossible); optional LLM mode sends masked evidence to an external provider; Streamlit CSS customisation depends on library version; single-process prototype; all data synthetic; financing terms illustrative.

## STRIDE threat model (initial skeleton; T16 completes it with code and test references)
- Spoofing: forged role or user. Controls: roles read from the user record, never from UI or parameters; PBKDF2 password hashes.
- Tampering: edited audit log or approvals. Controls: hash chain, append-only triggers, verify function, tamper test.
- Repudiation: denied actions. Controls: every login, denial, draft, approval and simulated execution is audited.
- Information disclosure: leaked data or secrets. Controls: masked evidence for llm mode, .env secrets, safe errors, secret scan.
- Denial of service: oversized uploads or heavy computation. Controls: size and row limits, caching, bounded Monte Carlo.
- Elevation of privilege: finance_ops approving, any role moving money. Controls: backend authorize(), MONEY_MOVEMENT always denied, tests.
- LLM-specific: prompt injection through uploaded text, excessive agency, unsafe output. Controls: untrusted-data handling, read-only tool whitelist, output validator, no execution by copilot. (When writing the mapping, check the current names at owasp.org; do not invent identifiers.)

