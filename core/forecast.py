"""Deterministic weekly cash forecasting and reserve-breach summaries."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median
from typing import Literal

from core.loaders import SyntheticCase

Layer = Literal["ACTUAL", "FORECAST"]
Severity = Literal["none", "watch", "critical"]


@dataclass(frozen=True)
class ForecastWeek:
    week_start: date
    layer: Layer
    inflow: float
    outflow: float
    net: float
    closing_balance: float


@dataclass(frozen=True)
class ForecastResult:
    weeks: list[ForecastWeek]
    actual_weeks: list[ForecastWeek]
    forecast_weeks: list[ForecastWeek]
    opening_cash: float
    reserve: float
    reserve_weeks: float
    fixed_weekly_outflow: float
    horizon_weeks: int
    shortage_week: int | None
    shortage_date: date | None
    below_zero_week: int | None
    minimum_balance: float
    minimum_balance_week: int
    funding_gap: float
    funding_buffer_pct: float
    severity: Severity
    run_rate_by_category: dict[str, float]
    payment_delay_days: dict[str, float]


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _actual_weeks(case: SyntheticCase) -> tuple[list[ForecastWeek], date | None, float]:
    indexed = sorted(enumerate(case.transactions), key=lambda item: (item[1].date, item[0]))
    if not indexed:
        return [], None, float(case.profile.opening_cash)
    grouped: dict[date, list] = defaultdict(list)
    for _, transaction in indexed:
        grouped[_week_start(transaction.date)].append(transaction)
    first_week, last_week = min(grouped), max(grouped)
    prior_balance = grouped[first_week][0].balance_after
    first_transaction = grouped[first_week][0]
    prior_balance -= first_transaction.amount if first_transaction.direction == "inflow" else -first_transaction.amount
    rows: list[ForecastWeek] = []
    current_balance = float(prior_balance)
    cursor = first_week
    while cursor <= last_week:
        transactions = grouped.get(cursor, [])
        inflow = sum(tx.amount for tx in transactions if tx.direction == "inflow")
        outflow = sum(tx.amount for tx in transactions if tx.direction == "outflow")
        if transactions:
            current_balance = float(transactions[-1].balance_after)
        rows.append(ForecastWeek(cursor, "ACTUAL", inflow, outflow, inflow - outflow, current_balance))
        cursor += timedelta(days=7)
    latest_balance = float(indexed[-1][1].balance_after)
    return rows, last_week, latest_balance


def _customer_delays(case: SyntheticCase, overrides: dict[str, float] | None) -> dict[str, float]:
    customers = {customer.customer_id: customer for customer in case.profile.customers}
    observed: dict[str, list[float]] = defaultdict(list)
    for invoice in case.receivables:
        if invoice.paid_date and invoice.paid_amount >= invoice.amount:
            observed[invoice.customer_id].append(float(max(0, (invoice.paid_date - invoice.due_date).days)))
    delays: dict[str, float] = {}
    for customer_id, customer in customers.items():
        if overrides and customer_id in overrides:
            delays[customer_id] = max(0.0, float(overrides[customer_id]))
        elif len(observed.get(customer_id, [])) >= 3:
            delays[customer_id] = float(median(observed[customer_id]))
        else:
            # Customer profile values are editable synthetic assumptions; an absent value defaults to zero.
            delays[customer_id] = float(customer.typical_delay_days)
    return delays


def forecast(
    case: SyntheticCase,
    *,
    horizon_weeks: int | None = None,
    reserve: float | None = None,
    reserve_weeks: float | None = None,
    funding_buffer_pct: float | None = None,
    payment_delays: dict[str, float] | None = None,
) -> ForecastResult:
    """Build actual and projected weekly cash rows for one validated case.

    The reserve can be supplied directly in currency units or derived from
    average fixed weekly outflows. Invoices and bills are excluded from
    category run-rate projections wherever their categories are identifiable.
    """
    assumptions = case.assumptions
    horizon = assumptions.forecast_horizon_weeks if horizon_weeks is None else int(horizon_weeks)
    if horizon < 8:
        raise ValueError("Forecast horizon must be at least 8 weeks.")
    weeks_of_reserve = assumptions.minimum_reserve_weeks if reserve_weeks is None else float(reserve_weeks)
    if weeks_of_reserve < 0:
        raise ValueError("Reserve weeks cannot be negative.")
    buffer_pct = assumptions.funding_buffer_pct if funding_buffer_pct is None else float(funding_buffer_pct)
    if buffer_pct < 0:
        raise ValueError("Funding buffer cannot be negative.")

    actual, latest_actual_week, opening_cash = _actual_weeks(case)
    if latest_actual_week is None:
        latest_actual_week = _week_start(date.today())
    first_forecast_week = latest_actual_week + timedelta(days=7)
    history_start = latest_actual_week - timedelta(days=7 * 7)
    recent_transactions = [tx for tx in case.transactions if history_start <= _week_start(tx.date) <= latest_actual_week]

    category_totals: dict[tuple[str, str], float] = defaultdict(float)
    for transaction in recent_transactions:
        category_totals[(transaction.direction, transaction.category)] += float(transaction.amount)
    run_rates: dict[str, float] = {
        f"{direction}:{category}": total / 8.0
        for (direction, category), total in category_totals.items()
    }
    discretionary_categories = {bill.category for bill in case.payables if bill.discretionary}
    fixed_weekly_outflow = sum(
        rate for key, rate in run_rates.items()
        if key.startswith("outflow:") and key.partition(":")[2] not in discretionary_categories
    )
    reserve_amount = float(reserve) if reserve is not None else weeks_of_reserve * fixed_weekly_outflow
    if reserve_amount < 0:
        raise ValueError("Reserve cannot be negative.")

    receivable_categories_present = bool(case.receivables)
    payable_categories = {bill.category for bill in case.payables}
    projected_run_rate: list[tuple[str, str, float]] = []
    for key, rate in run_rates.items():
        direction, _, category = key.partition(":")
        if direction == "inflow" and receivable_categories_present:
            continue
        if direction == "outflow" and category in payable_categories:
            continue
        projected_run_rate.append((direction, category, rate))

    delays = _customer_delays(case, payment_delays)
    forecast_inflows: dict[int, float] = defaultdict(float)
    forecast_outflows: dict[int, float] = defaultdict(float)

    def bucket(event_date: date) -> int:
        return max(0, (event_date - first_forecast_week).days // 7)

    for invoice in case.receivables:
        outstanding = max(0.0, float(invoice.amount - invoice.paid_amount))
        if outstanding <= 0:
            continue
        expected_date = invoice.due_date + timedelta(days=delays.get(invoice.customer_id, 0.0))
        index = bucket(expected_date)
        if index < horizon:
            forecast_inflows[index] += outstanding
    for bill in case.payables:
        outstanding = max(0.0, float(bill.amount - bill.paid_amount))
        if outstanding <= 0:
            continue
        index = bucket(bill.due_date)
        if index < horizon:
            forecast_outflows[index] += outstanding

    forecast_rows: list[ForecastWeek] = []
    closing = opening_cash
    for index in range(horizon):
        inflow = forecast_inflows[index]
        outflow = forecast_outflows[index]
        for direction, _category, rate in projected_run_rate:
            if direction == "inflow":
                inflow += rate
            else:
                outflow += rate
        closing += inflow - outflow
        forecast_rows.append(ForecastWeek(
            week_start=first_forecast_week + timedelta(days=7 * index),
            layer="FORECAST",
            inflow=inflow,
            outflow=outflow,
            net=inflow - outflow,
            closing_balance=closing,
        ))

    balances = [row.closing_balance for row in forecast_rows]
    minimum_balance = min(balances)
    minimum_index = balances.index(minimum_balance)
    shortage_index = next((index for index, balance in enumerate(balances) if balance < reserve_amount), None)
    below_zero_index = next((index for index, balance in enumerate(balances) if balance < 0), None)
    severity: Severity = "none" if shortage_index is None else ("critical" if below_zero_index is not None else "watch")
    raw_gap = max(0.0, reserve_amount - minimum_balance)
    funding_gap = raw_gap * (1 + buffer_pct / 100)
    return ForecastResult(
        weeks=actual + forecast_rows,
        actual_weeks=actual,
        forecast_weeks=forecast_rows,
        opening_cash=opening_cash,
        reserve=reserve_amount,
        reserve_weeks=weeks_of_reserve,
        fixed_weekly_outflow=fixed_weekly_outflow,
        horizon_weeks=horizon,
        shortage_week=shortage_index + 1 if shortage_index is not None else None,
        shortage_date=forecast_rows[shortage_index].week_start if shortage_index is not None else None,
        below_zero_week=below_zero_index + 1 if below_zero_index is not None else None,
        minimum_balance=minimum_balance,
        minimum_balance_week=minimum_index + 1,
        funding_gap=funding_gap,
        funding_buffer_pct=buffer_pct,
        severity=severity,
        run_rate_by_category=run_rates,
        payment_delay_days=delays,
    )
