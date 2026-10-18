"""Interactive grounded Copilot; every response carries its evidence receipt."""
from __future__ import annotations

import json

import streamlit as st

from app import components as ui
from app.assumptions_store import get_values, to_lab_assumptions
from core.loaders import load_case
from data.generate_synthetic import CASES
from services.auth import current_user
from services.copilot import answer_question

CASE_LABELS = {
    "stable_healthy": "Stable and healthy", "delayed_customer_payments": "Delayed customer payments",
    "high_expense_shortage": "High expense, shortage", "import_financing": "Import financing",
    "sales_drop_cost_rise": "Sales drop, cost rise",
}
SUGGESTIONS = (
    "Why will I run short of cash?", "How much funding do I need?", "Compare the plans",
    "What if customer delay increases by 7 days?", "What is the data quality?", "What is the readiness indicator?",
)

ui.load_styles()
user = current_user()
if user is None:
    st.warning("Sign in to ask the read-only Copilot.")
    st.stop()

active = st.session_state.get("active_synthetic_case", "high_expense_shortage")
case_name = st.selectbox("Synthetic demo case", CASES,
    index=CASES.index(active) if active in CASES else CASES.index("high_expense_shortage"),
    format_func=lambda value: CASE_LABELS[value], key="copilot-case-select")
case = load_case(case_name)
st.session_state["active_synthetic_case"] = case_name
st.session_state["synthetic_case_data"] = case
assumptions = to_lab_assumptions(get_values(case_name, case))
ui.page_header("Copilot", "Ask about the computed forecast, Decision Lab, analysis, and readiness evidence.",
               business=case.profile.business_name, scenario=CASE_LABELS[case_name])
st.caption("Synthetic data · BDT · read-only explanations. Customer and supplier names and free-text source fields are excluded from evidence.")
mode = __import__("os").getenv("COPILOT_MODE", "offline").strip().lower()
ui.alert_banner("info", "LLM mode" if mode == "llm" else "Offline mode",
    "LLM responses are checked against the same evidence and fall back to deterministic templates. No action is executed by Copilot." if mode == "llm"
    else "Answers are generated from deterministic application results and work without network access or an API key.")

ui.section_title("Suggested questions")
cols = st.columns(3)
for index, suggestion in enumerate(SUGGESTIONS):
    if cols[index % 3].button(suggestion, key=f"copilot-suggest-{index}", use_container_width=True):
        st.session_state["copilot_pending_question"] = suggestion

with st.form("copilot-ask-form", clear_on_submit=True):
    question = st.text_input("Ask a question", max_chars=500, key="copilot-question-input")
    submitted = st.form_submit_button("Ask Copilot", type="primary")
if submitted and question.strip():
    st.session_state["copilot_pending_question"] = question

pending = st.session_state.pop("copilot_pending_question", None)
if pending:
    try:
        result = answer_question(user, case, pending, assumptions)
        history = st.session_state.setdefault("copilot_answers", [])
        history.append({"question": pending, "answer": result.answer,
            "receipt": {"mode": result.receipt.mode, "evidence_ids": list(result.receipt.evidence_ids),
                "masked_fields": result.receipt.masked_fields, "external_call": result.receipt.external_call,
                "validator_result": result.receipt.validator_result},
            "evidence": result.evidence_pack["evidence"]})
    except ValueError as exc:
        st.error(str(exc))
    except Exception:  # noqa: BLE001 - keep internal errors and source data out of the UI
        st.error("Copilot could not complete this query. No action was taken; retry or check the local audit service.")

ui.section_title("Conversation")
for index, message in enumerate(st.session_state.get("copilot_answers", [])):
    with st.chat_message("user"):
        st.markdown(message["question"])
    with st.chat_message("assistant"):
        st.markdown(message["answer"])
        receipt = message["receipt"]
        st.caption(f"Receipt · Mode: {receipt['mode']} · Evidence: {', '.join(receipt['evidence_ids']) or 'none'} · "
                   f"Masked fields: {receipt['masked_fields']} · External call: {'yes' if receipt['external_call'] else 'no'} · "
                   f"Validator: {receipt['validator_result']}")
        with st.expander("Evidence used", key=f"copilot-evidence-{index}"):
            selected = set(receipt["evidence_ids"])
            for item in message["evidence"]:
                if item["id"] in selected:
                    st.markdown(f"**{item['id']} · {item['topic']}** — source: `{item['source']}`")
                    st.json(item["values"])

ui.footer()
