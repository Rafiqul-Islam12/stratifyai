"""Reliable historical business indicators with explicit availability reasons."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from core.loaders import SyntheticCase


@dataclass(frozen=True)
class Metric:
    value: float | None
    reason: str | None = None


@dataclass(frozen=True)
class BusinessAnalysis:
    as_of: date
    income: float
    expenses: float
    net_cash_flow: float
    weekly: tuple[dict[str, Any], ...]
    monthly: tuple[dict[str, Any], ...]
    expense_by_category: tuple[tuple[str, float], ...]
    income_by_category: tuple[tuple[str, float], ...]
    receivables_open: float
    receivables_overdue: float
    receivables_overdue_pct: Metric
    aging: dict[str, float]
    payables_open: float
    payables_due_next_4_weeks: float
    dso_days: Metric
    dpo_days: Metric
    burn_rate_weekly: Metric
    runway_weeks: Metric
    gross_margin_pct: Metric
    customer_concentration_pct: Metric
    expense_trend_flags: tuple[str, ...]
    insights: tuple[str, ...]


def analyze(case: SyntheticCase, *, as_of: date | None = None) -> BusinessAnalysis:
    """Summarize recorded transactions and open bills/invoices only.

    By default the data snapshot date is the latest recorded transaction date,
    which keeps synthetic and uploaded histories reproducible.
    """
    if as_of is None:
        as_of = max((tx.date for tx in case.transactions), default=date.today())
    week_rows: dict[date, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
    month_rows: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
    expense_categories: dict[str, float] = defaultdict(float)
    income_categories: dict[str, float] = defaultdict(float)
    for tx in case.transactions:
        week = tx.date - timedelta(days=tx.date.weekday())
        month = tx.date.strftime("%Y-%m")
        key = "income" if tx.direction == "inflow" else "expenses"
        week_rows[week][key] += float(tx.amount)
        month_rows[month][key] += float(tx.amount)
        if tx.direction == "outflow":
            expense_categories[tx.category] += float(tx.amount)
        else:
            income_categories[tx.category] += float(tx.amount)
    weekly_rows = []
    if week_rows:
        cursor = min(week_rows)
        last_week = max(week_rows)
        while cursor <= last_week:
            row = week_rows[cursor]
            weekly_rows.append({"week_start": cursor, **row, "net": row["income"] - row["expenses"]})
            cursor += timedelta(days=7)
    weekly = tuple(weekly_rows)
    monthly = tuple({"month": month, **month_rows[month], "net": month_rows[month]["income"] - month_rows[month]["expenses"]}
                    for month in sorted(month_rows))
    income = sum(float(tx.amount) for tx in case.transactions if tx.direction == "inflow")
    expenses = sum(float(tx.amount) for tx in case.transactions if tx.direction == "outflow")
    net = income - expenses
    recent_weeks = weekly[-13:]
    average_net = sum(row["net"] for row in recent_weeks) / len(recent_weeks) if recent_weeks else None

    open_invoices = [(invoice, max(0.0, float(invoice.amount - invoice.paid_amount)))
                     for invoice in case.receivables]
    open_invoices = [(invoice, amount) for invoice, amount in open_invoices if amount > 0]
    ar_open = sum(amount for _, amount in open_invoices)
    aging = {"0-30 days": 0.0, "31-60 days": 0.0, "61-90 days": 0.0, "90+ days": 0.0}
    overdue = 0.0
    for invoice, amount in open_invoices:
        days = max(0, (as_of - invoice.due_date).days)
        if invoice.due_date < as_of:
            overdue += amount
            # The 61-90 bucket includes day 90; 90+ means strictly more than 90.
            bucket = "0-30 days" if days <= 30 else "31-60 days" if days <= 60 else "61-90 days" if days <= 90 else "90+ days"
            aging[bucket] += amount
    overdue_pct = Metric(overdue / ar_open * 100 if ar_open else None,
                         None if ar_open else "there are no open receivables")
    open_bills = [(bill, max(0.0, float(bill.amount - bill.paid_amount))) for bill in case.payables]
    open_bills = [(bill, amount) for bill, amount in open_bills if amount > 0]
    ap_open = sum(amount for _, amount in open_bills)
    due_4w = sum(amount for bill, amount in open_bills if bill.due_date <= as_of + timedelta(days=28))

    history_start = min((tx.date for tx in case.transactions), default=as_of)
    history_days = max(1, (as_of - history_start).days + 1)
    credit_sales = sum(float(invoice.amount) for invoice in case.receivables
                       if history_start <= invoice.issue_date <= as_of)
    dso = (Metric(ar_open / credit_sales * history_days) if credit_sales > 0 else
           Metric(None, "receivable invoices issued during the transaction history are not available"))
    purchase_bills = [bill for bill in case.payables
                      if any(token in bill.category.lower() for token in ("inventory", "cogs", "cost of goods"))
                      and history_start <= bill.issue_date <= as_of]
    purchases = sum(float(bill.amount) for bill in purchase_bills)
    purchase_payables_open = sum(amount for bill, amount in open_bills
        if any(token in bill.category.lower() for token in ("inventory", "cogs", "cost of goods")))
    dpo = (Metric(purchase_payables_open / purchases * history_days) if purchases > 0 else
           Metric(None, "purchase bills issued during the transaction history are not available"))
    burn = Metric(max(0.0, -average_net) if average_net is not None else None,
                  None if average_net is not None else "no recorded weekly cash-flow history")
    cash = float(max(case.transactions, key=lambda tx: tx.date).balance_after) if case.transactions else float(case.profile.opening_cash)
    runway = Metric(cash / burn.value if burn.value and burn.value > 0 else None,
                    None if burn.value and burn.value > 0 else "recent recorded cash flow is not a net burn")
    direct_categories = {"cogs", "cost of goods sold", "inventory"}
    direct_cost = sum(value for category, value in expense_categories.items() if category.lower() in direct_categories)
    gross_margin = (Metric((income - direct_cost) / income * 100) if income > 0 and direct_cost > 0
                    else Metric(None, "income or a separately identified COGS/Inventory expense is missing"))
    by_customer: dict[str, float] = defaultdict(float)
    for invoice, amount in open_invoices:
        by_customer[invoice.customer_id] += amount
    concentration = Metric(max(by_customer.values()) / ar_open * 100 if ar_open > 0 else None,
                           None if ar_open > 0 else "there are no open receivables")

    flags = []
    for category in sorted(expense_categories):
        values = []
        for row in weekly:
            # Missing weeks count as zero, preserving the true weekly movement.
            values.append((row["week_start"], sum(float(tx.amount) for tx in case.transactions
                if tx.direction == "outflow" and tx.category == category and
                tx.date - timedelta(days=tx.date.weekday()) == row["week_start"])))
        if len(values) >= 8:
            prior = sum(value for _, value in values[-8:-4]) / 4
            recent = sum(value for _, value in values[-4:]) / 4
            if prior > 0 and recent > prior * 1.15:
                flags.append(f"{category} expenses increased {((recent / prior) - 1) * 100:.0f}% versus the prior four recorded weeks.")
    insights = [f"Recorded net cash flow is BDT {net:,.0f} across {len(weekly)} weeks."]
    if overdue:
        insights.append(f"BDT {overdue:,.0f} of open receivables are overdue as of {as_of.isoformat()}.")
    if flags:
        insights.extend(flags)
    return BusinessAnalysis(as_of, income, expenses, net, weekly, monthly,
        tuple(sorted(expense_categories.items(), key=lambda item: item[1], reverse=True)),
        tuple(sorted(income_categories.items(), key=lambda item: item[1], reverse=True)), ar_open, overdue, overdue_pct,
        aging, ap_open, due_4w, dso, dpo, burn, runway, gross_margin, concentration,
        tuple(flags), tuple(insights))
