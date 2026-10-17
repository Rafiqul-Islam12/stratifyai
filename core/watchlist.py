"""Explainable receivables risk scores based on docs/DECISIONS.md."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from core.loaders import SyntheticCase


@dataclass(frozen=True)
class CustomerWatch:
    customer_id: str
    customer_name: str
    open_balance: float
    overdue_balance: float
    score: float
    label: str
    invoice_ids: tuple[str, ...]
    component_scores: dict[str, float | None]


def receivables_watchlist(case: SyntheticCase, *, as_of: date | None = None) -> tuple[CustomerWatch, ...]:
    if as_of is None:
        as_of = max((tx.date for tx in case.transactions), default=date.today())
    customers = {customer.customer_id: customer.name for customer in case.profile.customers}
    open_by_customer: dict[str, list[tuple[object, float]]] = defaultdict(list)
    paid_delays: dict[str, list[tuple[date, float]]] = defaultdict(list)
    for invoice in case.receivables:
        if invoice.paid_date and invoice.paid_amount >= invoice.amount:
            paid_delays[invoice.customer_id].append((invoice.due_date,
                float(max(0, (invoice.paid_date - invoice.due_date).days))))
        outstanding = max(0.0, float(invoice.amount - invoice.paid_amount))
        if outstanding:
            open_by_customer[invoice.customer_id].append((invoice, outstanding))
    total_open = sum(amount for rows in open_by_customer.values() for _, amount in rows)
    output = []
    for customer_id, invoices in open_by_customer.items():
        open_balance = sum(amount for _, amount in invoices)
        overdue_rows = [(invoice, amount, max(0, (as_of - invoice.due_date).days))
                        for invoice, amount in invoices if invoice.due_date < as_of]
        overdue_balance = sum(amount for _, amount, _ in overdue_rows)
        overdue_share_score = overdue_balance / open_balance * 40 if open_balance else 0.0
        weighted_days_score = (sum(amount * min(days, 90) for _, amount, days in overdue_rows) /
                               open_balance / 90 * 30 if open_balance else 0.0)
        delays = sorted(paid_delays.get(customer_id, []), key=lambda row: row[0])
        trend_score = None
        if len(delays) >= 4:
            midpoint = len(delays) // 2
            earlier = sum(value for _, value in delays[:midpoint]) / midpoint
            recent_n = len(delays) - midpoint
            recent = sum(value for _, value in delays[midpoint:]) / recent_n
            trend_score = min(20.0, max(0.0, (recent - earlier) / 90 * 20))
        concentration_score = open_balance / total_open * 10 if total_open else 0.0
        components = {
            "overdue amount share (40)": overdue_share_score,
            "weighted days overdue (30)": weighted_days_score,
            "payment delay trend (20)": trend_score,
            "receivables concentration (10)": concentration_score,
        }
        known = [(score, weight) for score, weight in zip(components.values(), (40, 30, 20, 10)) if score is not None]
        # Components are weighted points, normalized when delay history is unavailable.
        score = sum(float(value) for value, _ in known) / sum(weight for _, weight in known) * 100
        label = "Normal" if score < 30 else "Watch" if score <= 60 else "Urgent"
        output.append(CustomerWatch(customer_id, customers.get(customer_id, customer_id), open_balance,
            overdue_balance, score, label, tuple(sorted(invoice.invoice_id for invoice, _ in invoices)), components))
    return tuple(sorted(output, key=lambda row: (-row.score, -row.overdue_balance, row.customer_id)))
