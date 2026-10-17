"""Evidence-based financing readiness indicator; never an approval prediction."""
from __future__ import annotations

import math
from dataclasses import dataclass

from core.analysis import BusinessAnalysis
from core.forecast import ForecastResult
from core.loaders import SyntheticCase

DEFAULT_WEIGHTS = {"repayment capacity": 35.0, "cash buffer": 25.0, "receivable quality": 20.0,
                   "data completeness": 10.0, "trend": 10.0}


@dataclass(frozen=True)
class ReadinessComponent:
    name: str
    weight: float
    score: float | None
    reason: str


@dataclass(frozen=True)
class ReadinessResult:
    score: float | None
    label: str
    components: tuple[ReadinessComponent, ...]
    reasons: tuple[str, ...]
    missing_information: tuple[str, ...]
    weights: dict[str, float]


def assess_readiness(
    case: SyntheticCase,
    analysis: BusinessAnalysis,
    projection: ForecastResult,
    *,
    capacity_ratio: float | None = None,
    weights: dict[str, float] | None = None,
) -> ReadinessResult:
    selected = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(selected) != set(DEFAULT_WEIGHTS) or any(not math.isfinite(value) or value < 0 for value in selected.values()):
        raise ValueError("Readiness weights must contain the five named, non-negative components")
    if sum(selected.values()) <= 0:
        raise ValueError("At least one readiness weight must be positive")
    reasons: list[str] = []
    missing: list[str] = []
    capacity_score = min(100.0, max(0.0, capacity_ratio / 1.25 * 100)) if capacity_ratio is not None else None
    capacity_reason = (f"Repayment capacity is {capacity_ratio:.2f}x; 1.25x maps to a full component score."
                       if capacity_ratio is not None else "Not available: no modelled monthly debt-service ratio.")
    if capacity_score is None:
        missing.append("A proposed facility amount, repayment schedule and monthly debt-service estimate.")
    cash = float(max(case.transactions, key=lambda tx: tx.date).balance_after) if case.transactions else float(case.profile.opening_cash)
    cash_score = min(100.0, max(0.0, cash / projection.reserve * 100)) if projection.reserve > 0 else None
    cash_reason = (f"Latest recorded cash is BDT {cash:,.0f} against a BDT {projection.reserve:,.0f} reserve."
                   if cash_score is not None else "Not available: the configured reserve is zero.")
    if cash_score is None:
        missing.append("A positive minimum cash reserve to compare with recorded cash.")
    ar_score = max(0.0, min(100.0, 100.0 - analysis.receivables_overdue / analysis.receivables_open * 100)) if analysis.receivables_open else None
    ar_reason = (f"Overdue open receivables are {analysis.receivables_overdue / analysis.receivables_open:.1%} of open receivables."
                 if ar_score is not None else "Not available: there are no open receivables.")
    if ar_score is None:
        missing.append("Open receivable records for the receivables-quality component.")
    sources = (bool(case.transactions), bool(case.receivables), bool(case.payables),
               bool(case.profile.customers), bool(case.profile.suppliers))
    completeness = sum(sources) / len(sources) * 100
    completeness_reason = f"{sum(sources)} of 5 core data sources contain records."
    for present, note in zip(sources, ("transaction history", "receivables", "payables", "customer profiles", "supplier profiles")):
        if not present:
            missing.append(f"Add {note}.")
    trend_score = None
    if len(analysis.weekly) >= 8:
        prior = sum(row["net"] for row in analysis.weekly[-8:-4]) / 4
        recent = sum(row["net"] for row in analysis.weekly[-4:]) / 4
        scale = max(abs(prior), abs(recent), 1.0)
        trend_score = min(100.0, max(0.0, 50.0 + 50.0 * (recent - prior) / scale))
        trend_reason = f"Average weekly net cash flow changed from BDT {prior:,.0f} to BDT {recent:,.0f} in the latest four weeks."
    else:
        trend_reason = "Not available: fewer than eight recorded weekly periods."
        missing.append("At least eight weekly transaction periods for a trend comparison.")
    components = (
        ReadinessComponent("repayment capacity", selected["repayment capacity"], capacity_score, capacity_reason),
        ReadinessComponent("cash buffer", selected["cash buffer"], cash_score, cash_reason),
        ReadinessComponent("receivable quality", selected["receivable quality"], ar_score, ar_reason),
        ReadinessComponent("data completeness", selected["data completeness"], completeness, completeness_reason),
        ReadinessComponent("trend", selected["trend"], trend_score, trend_reason),
    )
    available = [item for item in components if item.score is not None and item.weight > 0]
    total_weight = sum(item.weight for item in available)
    score = sum(item.score * item.weight for item in available) / total_weight if total_weight else None
    label = "Readiness indicator, not a loan approval prediction"
    reasons.extend(item.reason for item in components)
    return ReadinessResult(score, label, components, tuple(reasons), tuple(dict.fromkeys(missing)), selected)
