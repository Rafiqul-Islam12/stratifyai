"""Deterministic, illustrative financing calculations for the demo app."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from core.forecast import ForecastResult

Template = Literal["Term loan", "Invoice financing", "Supplier credit", "Credit line"]
TEMPLATES: tuple[Template, ...] = ("Term loan", "Invoice financing", "Supplier credit", "Credit line")


@dataclass(frozen=True)
class FinancingTerms:
    annual_rate_pct: float = 14.0
    fee_pct: float = 1.0
    tenor_months: int = 6
    advance_pct: float = 80.0


@dataclass(frozen=True)
class Installment:
    month: int
    opening_balance: float
    payment: float
    principal: float
    interest: float
    closing_balance: float


@dataclass(frozen=True)
class FinancingResult:
    template: Template
    gap: float
    amount: float
    terms: FinancingTerms
    schedule: tuple[Installment, ...]
    interest: float
    fees: float
    total_cost: float
    total_repayment: float
    debt_service_per_month: float
    capacity_ratio: float | None
    pressure_label: str
    risk_notes: tuple[str, ...]
    missing_information: tuple[str, ...]


def annuity_payment(principal: float, annual_rate_pct: float, months: int) -> float:
    """Equal monthly payment using a nominal annual rate divided by 12."""
    _validate(principal, annual_rate_pct, months)
    if principal == 0:
        return 0.0
    monthly_rate = annual_rate_pct / 100 / 12
    if monthly_rate == 0:
        return principal / months
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)


def _validate(amount: float, annual_rate_pct: float, months: int, fee_pct: float = 0.0, advance_pct: float = 80.0) -> None:
    if not math.isfinite(amount) or amount < 0:
        raise ValueError("Amount must be a finite non-negative number.")
    if not math.isfinite(annual_rate_pct) or annual_rate_pct < 0 or annual_rate_pct > 100:
        raise ValueError("Annual rate must be between 0 and 100 percent.")
    if not 1 <= months <= 120:
        raise ValueError("Tenor must be between 1 and 120 months.")
    if not math.isfinite(fee_pct) or fee_pct < 0 or fee_pct > 100:
        raise ValueError("Fee must be between 0 and 100 percent.")
    if not math.isfinite(advance_pct) or not 1 <= advance_pct <= 100:
        raise ValueError("Advance percentage must be between 1 and 100 percent.")


def funding_amount(gap: float, template: Template, advance_pct: float = 80.0) -> float:
    """Round the required facility up to the next BDT 1,000; zero stays zero.

    Invoice financing is grossed up by its advance percentage to deliver the
    requested net cash. Other templates are sized directly to the rounded gap.
    """
    _validate(gap, 0, 1, advance_pct=advance_pct)
    if template not in TEMPLATES:
        raise ValueError("Unknown financing template.")
    rounded_gap = math.ceil(gap / 1000) * 1000 if gap else 0
    return rounded_gap / (advance_pct / 100) if template == "Invoice financing" else rounded_gap


def calculate_financing(
    template: Template,
    gap: float,
    terms: FinancingTerms,
    forecast: ForecastResult,
) -> FinancingResult:
    """Calculate schedule, costs, capacity and fixed-rule explanatory notes."""
    _validate(gap, terms.annual_rate_pct, terms.tenor_months, terms.fee_pct, terms.advance_pct)
    if template not in TEMPLATES:
        raise ValueError("Unknown financing template.")
    amount = funding_amount(gap, template, terms.advance_pct)
    n = terms.tenor_months
    rate = terms.annual_rate_pct / 100 / 12
    rows: list[Installment] = []
    interest = 0.0
    if amount > 0 and template == "Term loan":
        payment = annuity_payment(amount, terms.annual_rate_pct, n)
        balance = amount
        for month in range(1, n + 1):
            charge = balance * rate
            principal = min(balance, payment - charge)
            closing = max(0.0, balance - principal)
            if month == n:
                principal, closing = balance, 0.0
            fee_charge = amount * terms.fee_pct / 100 if month == 1 else 0.0
            paid = principal + charge + fee_charge
            interest += charge
            rows.append(Installment(month, balance, paid, principal, charge, closing))
            balance = closing
    elif amount > 0 and template == "Credit line":
        charge = amount * rate
        interest = charge * n
        rows.extend(Installment(month, amount, charge + (amount if month == n else 0)
                                + (amount * terms.fee_pct / 100 if month == 1 else 0),
                                0 if month < n else amount, charge, amount if month < n else 0)
                    for month in range(1, n + 1))
    elif amount > 0:
        # Invoice financing and supplier credit are modelled as a single
        # principal repayment at maturity; their periodic charge is explicit.
        if template == "Invoice financing":
            period_charge = amount * terms.fee_pct / 100
            interest = period_charge * n
            fees = 0.0
        else:
            interest = 0.0
            fees = amount * terms.fee_pct / 100
            period_charge = 0.0
        rows.extend(Installment(month, amount,
                                amount + period_charge + (fees if month == n else 0) if month == n else period_charge,
                                amount if month == n else 0,
                                period_charge + (fees if month == n else 0),
                                amount if month < n else 0) for month in range(1, n + 1))
    else:
        fees = 0.0

    if amount > 0 and template not in ("Supplier credit", "Invoice financing"):
        fees = amount * terms.fee_pct / 100
    total_cost = interest + fees
    total_repayment = amount + total_cost
    service = max((row.payment for row in rows), default=0.0)
    average_weekly_net = sum(week.net for week in forecast.forecast_weeks) / max(1, len(forecast.forecast_weeks))
    ratio = (average_weekly_net * (52 / 12)) / service if service > 0 else None
    pressure = "No repayment" if service == 0 else "Comfortable" if ratio is not None and ratio >= 1.25 else "Tight" if ratio is not None and ratio >= 1 else "Stressed"
    risk = []
    if amount == 0:
        risk.append("The projected funding gap is zero; no facility is sized.")
    if rows and template in ("Supplier credit", "Invoice financing", "Credit line"):
        risk.append("Principal is repaid as a lump sum at maturity; plan for that cash outflow.")
    if ratio is not None and ratio < 1:
        risk.append("Projected operating cash flow is below the modelled monthly debt service.")
    if template == "Invoice financing":
        risk.append("Assumes eligible invoices and an 80% default advance; invoice eligibility is unverified.")
    missing = ["Lender or supplier quote and complete contractual terms", "Historical repayment performance and actual cash-flow seasonality"]
    if template == "Invoice financing":
        missing.append("Invoice eligibility, concentration limits and recourse terms")
    return FinancingResult(template, gap, amount, terms, tuple(rows), interest, fees, total_cost,
                           total_repayment, service, ratio, pressure, tuple(risk), tuple(missing))
