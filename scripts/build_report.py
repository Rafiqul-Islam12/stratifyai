#!/usr/bin/env python3
"""Compile existing evaluation artifacts into judge-facing Markdown and HTML."""
from __future__ import annotations

import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
REPORTS = ROOT / "reports"


def _read(name: str) -> str:
    path = EVIDENCE / name
    return path.read_text(encoding="utf-8") if path.is_file() else f"Evidence not available: {name}. Run `python run.py eval` and `python scripts/run_tasks.py`."


def build() -> tuple[str, str]:
    plan = (ROOT / "docs" / "PLAN.md").read_text(encoding="utf-8")
    statuses = re.findall(r"^- \[([ x])\] T\d{2} ", plan, re.M)
    done = statuses.count("x")
    total = len(statuses)
    decision_text = _read("decision_quality.json")
    try:
        decisions = json.loads(decision_text)
        decision_summary = [f"- {row['case']}: {row['recommended_plan']}; reserve maintained: {row['keeps_reserve']}; minimum BDT {row['minimum_balance_bdt']:,.2f} vs reserve BDT {row['reserve_bdt']:,.2f}; breach probability {row['breach_probability']:.2%}." for row in decisions]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        decision_summary = ["Decision-quality evidence is unavailable or invalid; rerun the evaluation."]
    test_text = _read("test_results.txt")
    exit_match = re.search(r"^Exit code: (\d+)$", test_text, re.M)
    task_text = _read("task_suite_results.md")
    sections = [
        "# StratifyAI evaluation report", "", f"Generated: {datetime.now(UTC).isoformat(timespec='seconds')}", "",
        "## Scope and caveat", "", "This report uses synthetic case data only. Forecast and decision-quality metrics are an offline evaluation, not a claim of live or production accuracy. Financing terms and scenario changes are illustrative and hypothetical.", "",
        "## Backtest against naive baseline", "", _read("backtest_results.md"), "",
        "## Decision quality", "", *decision_summary, "",
        "## Security evaluation", "", _read("security_eval.md"), "",
        "## Scripted task suite", "", task_text, "",
        "## Test suite", "", f"Recorded pytest exit code: {exit_match.group(1) if exit_match else 'not available'}", "", "```text", test_text, "```", "",
        "## Checklist status", "", f"Tasks complete: {done}/{total} ({done / total:.1%})" if total else "Task checklist unavailable.", "",
        "## Evidence files", "", "- `evidence/backtest_results.csv` and `.md`", "- `evidence/decision_quality.json`", "- `evidence/security_eval.md`", "- `evidence/task_suite_results.md`", "- `evidence/test_results.txt`", "",
        "## Limitations", "", "The backtest is based on a small synthetic holdout set; results may be poor and should be read alongside the naive baseline. The decision-quality check recomputes the selected Lab plan using the same deterministic engines and reports the seeded uncertainty estimate. No result implies a lender decision, customer payment, supplier agreement, or real-world execution."
    ]
    markdown = "\n".join(sections) + "\n"
    escaped = html.escape(markdown)
    html_doc = "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>StratifyAI Evaluation Report</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:960px;margin:3rem auto;padding:0 1.2rem;color:#17212b;background:#f7f9fb}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;padding:1rem;border:1px solid #d9e0e7;border-radius:8px}h1,h2{line-height:1.25}a{color:#006b70}</style></head><body><pre>" + escaped + "</pre></body></html>\n"
    return markdown, html_doc


def main() -> int:
    REPORTS.mkdir(exist_ok=True)
    markdown, html_doc = build()
    (REPORTS / "final_report.md").write_text(markdown, encoding="utf-8")
    (REPORTS / "final_report.html").write_text(html_doc, encoding="utf-8")
    print(f"Built {REPORTS / 'final_report.md'} and {REPORTS / 'final_report.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
