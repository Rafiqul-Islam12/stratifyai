# Security Self-Assessment

**Scope:** synthetic-data Streamlit prototype, publicly deployed at [stratifyai-avuusk24epzvvcaegax2uq.streamlit.app](https://stratifyai-avuusk24epzvvcaegax2uq.streamlit.app/). This document is a project self-assessment, not a deployment penetration test, certification or production approval.

## Permission-tier implementation

| Action | Tier | Allowed roles | Enforcement location | Test reference |
| --- | --- | --- | --- | --- |
| `dashboard.view`, `security.view` | READ | owner, finance_ops, viewer, auditor | `services/permissions.py` (`ACTION_REGISTRY`, `authorize`) | `tests/test_security.py::test_role_action_matrix_and_denials_are_logged` |
| `copilot.ask` | READ | owner, finance_ops, viewer, auditor | `services/copilot.py::answer_question` calls backend `authorize` | `tests/test_copilot.py::test_offline_answers_are_grounded_and_have_audited_receipts`; `test_permission_denial_and_unvalidated_llm_output_fall_back` |
| `audit.view` | READ | owner, auditor | `services/audit.py::get_audit_events`, `verify_audit_chain` | `tests/test_security.py::test_role_action_matrix_and_denials_are_logged`; `test_audit_chain_sanitizes_and_detects_tampering` |
| `approvals.view` | READ | owner, finance_ops, auditor | `services/agent_actions.py::list_drafts` | `tests/test_agent_actions.py::test_roles_and_transition_rules_are_enforced_and_audited` |
| `draft.view` | READ | owner, finance_ops; finance_ops sees own drafts | `services/agent_actions.py::get_draft` | `tests/test_agent_actions.py::test_roles_and_transition_rules_are_enforced_and_audited` |
| `lab.run`, `scenario.change`, `data.upload`, `draft.create` | DRAFT | owner, finance_ops | `services/actions.py`, `services/agent_actions.py`, `services/permissions.py` | `tests/test_agent_actions.py::test_roles_and_transition_rules_are_enforced_and_audited`; `tests/test_validation.py::test_upload_page_accepts_good_file_and_stores_validated_rows` |
| `assumptions.manage` | DRAFT | owner | `services/permissions.py`; assumptions page uses the registry | `tests/test_agent_actions.py::test_roles_and_transition_rules_are_enforced_and_audited`; `tests/test_lab_page.py::test_assumptions_page_edits_and_reset_restore_defaults` |
| `draft.approve`, `draft.reject` | APPROVAL_REQUIRED | owner | `services/agent_actions.py::review_draft` checks both role and pending state | `tests/test_agent_actions.py::test_owner_approval_rejection_and_execution_are_idempotent`; `test_roles_and_transition_rules_are_enforced_and_audited` |
| `execution.simulate` | APPROVAL_REQUIRED | owner | `services/agent_actions.py::simulate_execution` requires approved state; writes local log | `tests/test_agent_actions.py::test_owner_approval_rejection_and_execution_are_idempotent`; `test_full_finance_ops_to_owner_ui_flow` |
| `money.move` | MONEY_MOVEMENT | None; denied for every role | `services/permissions.py::authorize`; `services/actions.py::move_money` | `tests/test_security.py::test_money_movement_denied_for_every_role_including_owner` |

The role returned by authorization is resolved from the issued server-side session token and user record. UI visibility is not the control boundary. Denials are audit events.

## STRIDE threat model

| STRIDE threat | Example | Implemented control | Test evidence | Residual risk |
| --- | --- | --- | --- | --- |
| Spoofing | Forged username or role in Streamlit session state | Salted PBKDF2-HMAC-SHA256 password hashes; issued session token; service resolves principal from server state | `tests/test_security.py::test_password_login_logout_and_server_side_role_resolution` | Demo credentials and password-free shortcuts are for local synthetic demonstrations; no MFA or production identity provider |
| Tampering | Modify approval state or audit history on disk | State-checked transitions; SQLite update/delete triggers; SHA-256 previous-hash chain and verifier | `tests/test_agent_actions.py::test_owner_approval_rejection_and_execution_are_idempotent`; `tests/test_security.py::test_audit_chain_sanitizes_and_detects_tampering` | A local database administrator can replace the file or disable triggers; the chain detects edits but is not immutable storage |
| Repudiation | User denies submitting or approving a draft | Draft, approval, denial, login and simulated-execution events include actor, role, action and chained record | `tests/test_security.py::test_role_action_matrix_and_denials_are_logged`; `tests/test_agent_actions.py::test_full_finance_ops_to_owner_ui_flow` | Local operator access can delete or replace the database; clocks and host identity are not independently attested |
| Information disclosure | Customer names, raw queries or provider keys enter evidence, logs or output | Copilot evidence omits names/free text; query hash rather than raw query is audited; audit sanitizer removes sensitive-looking fields; secrets stay in `.env` | `tests/test_copilot.py::test_untrusted_customer_names_and_invoice_text_never_enter_evidence`; `tests/test_security.py::test_audit_chain_sanitizes_and_detects_tampering`; `tests/test_smoke.py::test_check_secrets_is_clean` | Configured LLM provider receives the question and masked numerical evidence; provider retention/reachability is outside project control |
| Denial of service | Oversized upload or pathological question/provider call | 5 MiB upload limit, 50,000-row cap, 500-character text/question limits, 20-second provider timeout, bounded response read | `tests/test_validation.py::test_oversized_file_is_rejected`; `test_row_limit_is_reported_without_silently_dropping_rows`; `tests/test_copilot.py::test_unknown_question_returns_missing_data_and_question_limits_are_enforced` | No request-rate limit, per-user quota or concurrent-job scheduler; a single local process can still be exhausted |
| Elevation of privilege | finance_ops approves; viewer moves money; Copilot invokes a privileged action | Backend `authorize`; owner-only approval/simulation; `MONEY_MOVEMENT` has no allowed roles; Copilot is read-only and has no action tools | `tests/test_security.py::test_role_action_matrix_and_denials_are_logged`; `test_money_movement_denied_for_every_role_including_owner`; `tests/test_agent_actions.py::test_roles_and_transition_rules_are_enforced_and_audited` | Local source-code or database administrator can alter the prototype; no deployment hardening or tenant isolation |

## LLM application risk mapping

The current OWASP GenAI LLM Top 10 is the 2026 edition. Names below follow the official [OWASP GenAI LLM Top 10 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) and its [published PDF](https://genai.owasp.org/download/56857/?tmstv=1785822482). Mapping is an internal assessment, not OWASP validation.

| OWASP 2026 risk | Relevance and control in this prototype | Evidence / gap |
| --- | --- | --- |
| LLM01:2026 Prompt Injection | Direct question and imported free text are untrusted data; a narrow supported-intent path, masked evidence, no tools and no execution bound impact | `tests/test_copilot.py::test_untrusted_customer_names_and_invoice_text_never_enter_evidence` covers 10 payloads. Regex filtering is not a general prompt-injection solution |
| LLM02:2026 Sensitive Information Disclosure | Names and source free text are excluded from the evidence pack; audit stores a SHA-256 query hash and receipt | Injection/masking and audit sanitizer tests above. Optional provider still sees the question and masked business numbers |
| LLM03:2026 Excessive Agency | Copilot has no tools that can approve, draft or execute. Drafts are separate services with owner-only checks; money movement is always denied | `test_money_movement_denied_for_every_role_including_owner`; `test_full_finance_ops_to_owner_ui_flow` |
| LLM04:2026 Supply Chain | Runtime dependencies are pinned in `requirements.txt` | No SBOM, provenance verification or automated dependency vulnerability scan is implemented |
| LLM05:2026 Data and Model Poisoning | No model training, fine-tuning, vector store or persistent retrieval corpus exists; uploaded data is validated and remains untrusted | Upload validation tests exist; no model/data-poisoning red-team suite |
| LLM06:2026 Unbounded Consumption | Question and provider response are bounded; provider timeout is 20 seconds; uploads have byte/row/text limits | Question/upload limit tests. No rate limits or per-user/provider cost budgets |
| LLM07:2026 Misinformation | Every factual sentence needs a known evidence ID; every numeric literal must match computed evidence; invalid output falls back offline | `tests/test_copilot.py::test_llm_output_must_cite_grounded_numbers_and_unconfigured_mode_makes_no_call`; `test_permission_denial_and_unvalidated_llm_output_fall_back` |
| LLM08:2026 Hidden Context Exposure | Provider credentials are environment settings, not inserted in evidence; the prompt contains no credential values | No dedicated system-prompt extraction test; optional provider request and provider controls are not independently audited |
| LLM09:2026 Vector and Embedding Weaknesses | Not applicable to current architecture: no embeddings, vector database or RAG index | No implementation or vector-specific test |
| LLM10:2026 Improper Output Handling | Candidate text is checked for evidence IDs and numerical grounding before display; Streamlit renders markdown with its default `unsafe_allow_html=False` | Grounding/fallback tests exist; no broad browser output-sanitization or adversarial Markdown suite |

## Known risks and mitigations

- **Demo identity and public access:** seeded demo accounts and password-free quick-sign-in buttons are intended only for synthetic demonstrations. The public Streamlit deployment has no production identity provider, MFA, or tenant isolation. Do not upload real business, customer, personal, financial, credential, or other sensitive information. Local demo passwords can be changed in ignored `.env`.
- **Local storage trust:** SQLite triggers and hash links reveal many accidental edits but cannot stop a host administrator from replacing the database. Export or replicate audit events to a separately controlled append-only store before any real deployment.
- **External LLM:** offline is the default. In `llm` mode, a user-selected endpoint receives the question and masked evidence pack. Review provider privacy, retention, region and contractual terms before configuring it. No API key is required for offline demo.
- **Forecast quality:** the current synthetic holdout model MAE is higher than the naive baseline on all five cases; four of five selected plans fail to keep reserve. Do not use results for real credit or cash decisions.
- **Availability:** single-process prototype, no rate limiter, no production database, no tenant isolation and no backup/recovery runbook.
- **Financial product scope:** all cases are synthetic; facilities are editable illustrations; no lender approval, loan submission, payment or bank integration exists.

## Not implemented

Production SSO/MFA, tenant isolation, production secrets manager, service-level monitoring, rate limits, dependency vulnerability scanning/SBOM, disaster recovery, provider contracts, RAG/vector search, model fine-tuning, autonomous agent tools, real bank or lender APIs, real loan applications and real money movement are not implemented. These require separate security, legal, privacy and operational review.