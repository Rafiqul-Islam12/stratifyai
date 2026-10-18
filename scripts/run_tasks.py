#!/usr/bin/env python3
"""Run the scripted service-level task-completion suite and save its real results."""
from __future__ import annotations

import json
import math
import sqlite3
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.analysis import analyze
from core.audit import log_event, verify_chain
from core.financing import FinancingTerms, calculate_financing
from core.forecast import forecast
from core.lab import run_lab
from core.loaders import load_case
from core.stress import StressInputs, apply_stress
from services.agent_actions import create_draft, review_draft, submit_draft
from services.auth import DEMO_PASSWORD_DEFAULTS, login
from services.copilot import answer_question, validate_answer
from services.permissions import PermissionDenied, authorize
from services.validation import validate_upload

TASKS = json.loads((ROOT / "tests" / "tasks" / "tasks.json").read_text(encoding="utf-8"))


def run_task(task: dict) -> None:
    case_name = task["case"]
    case = load_case(case_name)
    task_id = task["id"]
    with tempfile.TemporaryDirectory(prefix=f"stratify-{task_id}-") as tmp:
        audit = Path(tmp) / "audit.sqlite3"
        drafts = Path(tmp) / "drafts.sqlite3"
        if task_id == "T01":
            result = forecast(case)
            assert result.shortage_week is not None, "no shortage week in this case"
        elif task_id == "T02":
            plans = run_lab(case).plans
            assert {"Option 0", "L1", "L2", "L3", "Option A", "Option B", "Option C"} <= plans.keys()
        elif task_id == "T03":
            result = run_lab(case)
            chosen = result.plans[result.best_plan_id]
            assert chosen.is_feasible and min(x.closing_balance for x in chosen.balance_series_after) >= result.reserve - 1e-7
        elif task_id == "T04":
            original = case.transactions[0].amount
            result = apply_stress(case, StressInputs(sales_drop_pct=20, cost_increase_pct=15, customer_delay_days=14, fx_shock_pct=10))
            assert math.isfinite(forecast(result.case).minimum_balance)
            assert case.transactions[0].amount == original
        elif task_id == "T05":
            gap = forecast(case).funding_gap
            result = calculate_financing(gap, FinancingTerms())
            assert result.amount >= 0 and result.total_cost >= 0 and isinstance(result.schedule, tuple)
        elif task_id == "T06":
            ops = login("finance_ops", DEMO_PASSWORD_DEFAULTS["finance_ops"], session_state={}, db_path=audit)
            invoice = next((x for x in case.receivables if x.paid_amount < x.amount), None)
            assert invoice is not None
            customer = next(x.name for x in case.profile.customers if x.customer_id == invoice.customer_id)
            draft = create_draft(ops, "collection_reminder", {"customer": customer, "invoice": invoice.invoice_id,
                "amount": invoice.amount - invoice.paid_amount, "due_date": invoice.due_date.isoformat()}, db_path=drafts)
            assert draft.status == "draft" and draft.payload["execution_policy"] == "manual review only"
        elif task_id == "T07":
            ops = login("finance_ops", DEMO_PASSWORD_DEFAULTS["finance_ops"], session_state={}, db_path=audit)
            owner = login("owner", DEMO_PASSWORD_DEFAULTS["owner"], session_state={}, db_path=audit)
            invoice = next(x for x in case.receivables if x.paid_amount < x.amount)
            customer = next(x.name for x in case.profile.customers if x.customer_id == invoice.customer_id)
            draft = create_draft(ops, "collection_reminder", {"customer": customer, "invoice": invoice.invoice_id,
                "amount": invoice.amount - invoice.paid_amount, "due_date": invoice.due_date.isoformat()}, db_path=drafts)
            submitted = submit_draft(ops, draft.draft_id, db_path=drafts)
            assert submitted.status == "pending_approval"
            approved = review_draft(owner, draft.draft_id, "approve", "Task-suite owner approval", db_path=drafts)
            assert approved.status == "approved" and approved.reviewer == "owner"
        elif task_id == "T08":
            viewer = login("viewer", DEMO_PASSWORD_DEFAULTS["viewer"], session_state={}, db_path=audit)
            try:
                authorize(viewer, "lab.run", db_path=str(audit))
            except PermissionDenied:
                assert not verify_chain(db_path=audit).ok is False or verify_chain(db_path=audit).ok
            else:
                raise AssertionError("viewer was unexpectedly authorized")
        elif task_id == "T09":
            csv_data = b"transaction_id,date,description,category,amount,direction,balance_after\nT1,2026-01-01,=1+1,Sales,1,inflow,1\n"
            result = validate_upload("transactions.csv", csv_data)
            assert result.cleaned_data and result.cleaned_data[0]["description"].startswith("'")
            assert any("neutralised" in item.message for item in result.warnings)
        elif task_id == "T10":
            log_event("owner", "owner", "task.check", "audit", db_path=audit)
            assert verify_chain(db_path=audit).ok
        elif task_id == "T11":
            log_event("owner", "owner", "task.check", "audit", db_path=audit)
            with sqlite3.connect(audit) as db:
                db.execute("DROP TRIGGER audit_log_no_update")
                db.execute("UPDATE audit_log SET entity='tampered' WHERE id=1")
            assert not verify_chain(db_path=audit).ok
        elif task_id == "T12":
            owner = login("owner", DEMO_PASSWORD_DEFAULTS["owner"], session_state={}, db_path=audit)
            answer = answer_question(owner, case, "How much funding do I need?", db_path=str(audit))
            valid, evidence_ids, reason = validate_answer(answer.answer, answer.evidence_pack)
            assert valid and evidence_ids, reason
        elif task_id == "T13":
            result = analyze(case)
            assert result.snapshot_date is not None
            assert all(math.isfinite(value) for value in result.weekly_net_cash_flow.values())
        else:
            raise ValueError(f"Unknown task {task_id}")


def main() -> int:
    results = []
    for task in TASKS:
        try:
            run_task(task)
            results.append((task, True, "expected outcome observed"))
        except Exception as exc:  # report one task failure while continuing the suite
            results.append((task, False, f"{type(exc).__name__}: {exc}"))
    passed = sum(ok for _, ok, _ in results)
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    lines = ["# Scripted task-completion suite", "", f"Evaluated: {stamp}", "",
             f"Overall: {passed}/{len(results)} passed ({passed / len(results):.1%}).", "",
             "| ID | Case | Steps | Expected result | Result | Detail |", "|---|---|---|---|---|---|"]
    for task, ok, detail in results:
        steps = "; ".join(task["steps"]).replace("|", "\\|")
        expected = task["expected"].replace("|", "\\|")
        lines.append(f"| {task['id']} | {task['case']} | {steps} | {expected} | {'PASS' if ok else 'FAIL'} | {detail.replace('|', '/') } |")
    output = ROOT / "evidence" / "task_suite_results.md"
    output.parent.mkdir(exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
