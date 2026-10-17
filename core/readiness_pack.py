"""Markdown readiness packs with content-integrity verification."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

from core.analysis import BusinessAnalysis
from core.forecast import ForecastResult
from core.loaders import SyntheticCase
from core.readiness import ReadinessResult

HASH_LINE = re.compile(r"([0-9a-f]{64})(?:\r?\n)?")


@dataclass(frozen=True)
class ReadinessPack:
    content: str
    content_hash: str
    generated_at: str
    expires_on: date
    consent: bool


def _money(value: float) -> str:
    return f"BDT {value:,.0f}"


def build_readiness_pack(
    case: SyntheticCase,
    analysis: BusinessAnalysis,
    projection: ForecastResult,
    readiness: ReadinessResult,
    *,
    chosen_plan: str,
    assumptions: dict[str, object],
    expires_on: date,
    consent: bool,
    generated_at: datetime | None = None,
) -> ReadinessPack:
    """Build a reproducible Markdown snapshot; consent and expiry are explicit."""
    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None:
        raise ValueError("generated_at must include a timezone")
    if expires_on < generated.date():
        raise ValueError("Expiry date cannot be earlier than the generation date")
    lines = [
        "# StratifyAI Readiness Pack", "",
        "**Integrity check only. Not a lender submission.**", "",
        f"- Business: {case.profile.business_name}",
        f"- Generated (UTC): {generated.astimezone(UTC).isoformat()}",
        f"- Expires on: {expires_on.isoformat()}",
        f"- User consent recorded: {'Yes' if consent else 'No'}", "",
        "## Business summary", "",
        f"- Recorded income: {_money(analysis.income)}",
        f"- Recorded expenses: {_money(analysis.expenses)}",
        f"- Recorded net cash flow: {_money(analysis.net_cash_flow)}",
        f"- Open receivables: {_money(analysis.receivables_open)} ({_money(analysis.receivables_overdue)} overdue)",
        f"- Open payables: {_money(analysis.payables_open)}",
        "", "## 13-week outlook", "",
        f"- Forecast horizon: {projection.horizon_weeks} weeks; minimum reserve: {_money(projection.reserve)}",
        f"- Forecast minimum: {_money(projection.minimum_balance)} in week {projection.minimum_balance_week}",
        f"- Funding gap: {_money(projection.funding_gap)}",
        f"- First reserve breach: {projection.shortage_week if projection.shortage_week is not None else 'None'}",
        "", "| Week | Date | Inflow | Outflow | Closing balance |",
        "|---:|---|---:|---:|---:|",
    ]
    lines.extend(
        f"| {index} | {week.week_start.isoformat()} | {_money(week.inflow)} | {_money(week.outflow)} | {_money(week.closing_balance)} |"
        for index, week in enumerate(projection.forecast_weeks, start=1)
    )
    lines.extend([
        "", "## Decision Lab plan", "", f"- Selected plan: {chosen_plan}", "",
        "## Assumptions", "",
    ])
    lines.extend(f"- {key}: {value}" for key, value in sorted(assumptions.items()))
    lines.extend(["", "## Readiness indicator", "", f"- Label: {readiness.label}",
                  f"- Score: {f'{readiness.score:.1f} / 100' if readiness.score is not None else 'Not available'}"])
    lines.extend(f"- {item.name} ({item.weight:g}% weight): "
                 f"{f'{item.score:.1f}' if item.score is not None else 'Not available'} — {item.reason}"
                 for item in readiness.components)
    lines.extend(["", "## Data-quality notes", ""])
    unavailable = [f"{name}: {metric.reason}" for name, metric in (
        ("DSO", analysis.dso_days), ("DPO", analysis.dpo_days),
        ("Gross margin", analysis.gross_margin_pct), ("Runway", analysis.runway_weeks),
    ) if metric.value is None]
    quality_notes = [*readiness.missing_information, *unavailable]
    lines.extend(f"- {note}" for note in (quality_notes or ("No missing core data source or unavailable headline metric was flagged.",)))
    lines.extend(["", "## Disclaimers", "",
        "This pack summarizes synthetic or user-provided records and model assumptions. It does not verify source documents, provide credit advice, predict approval, or submit information to a lender.",
        "The readiness score is an explainable indicator only. Confirm all figures and assumptions before sharing.", ""])
    body = "\n".join(lines)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    content = f"{body}Content SHA-256: {digest}\n"
    return ReadinessPack(content, digest, generated.astimezone(UTC).isoformat(), expires_on, consent)


def verify_readiness_pack(content: str) -> tuple[bool, str]:
    """Return whether the Markdown body matches its embedded SHA-256 digest."""
    marker = "Content SHA-256: "
    if content.count(marker) != 1:
        return False, "No valid content hash was found."
    body, suffix = content.split(marker, 1)
    match = HASH_LINE.fullmatch(suffix)
    if not match or not body.endswith("\n"):
        return False, "No valid final content hash was found."
    expected = match.group(1)
    actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if actual != expected:
        return False, "Integrity check failed: the pack content or hash has changed."
    return True, "Integrity check passed. This confirms content consistency only; it does not verify facts or lender submission."
