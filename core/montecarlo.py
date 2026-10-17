"""Vectorised, seeded cash-flow uncertainty simulation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from core.forecast import ForecastResult, forecast
from core.loaders import SyntheticCase


@dataclass(frozen=True)
class MonteCarloResult:
    week_starts: tuple[date, ...]
    p10: tuple[float, ...]
    p50: tuple[float, ...]
    p90: tuple[float, ...]
    probability_below_reserve: tuple[float, ...]
    probability_below_zero: tuple[float, ...]
    probability_any_reserve_breach: float
    runs: int
    seed: int


def simulate(
    case: SyntheticCase,
    *,
    projection: ForecastResult | None = None,
    inflows: tuple[float, ...] | list[float] | None = None,
    outflows: tuple[float, ...] | list[float] | None = None,
    balance_adjustments: tuple[float, ...] | list[float] | None = None,
    opening_cash: float | None = None,
    reserve: float | None = None,
    sales_variability_cv: float | None = None,
    customer_delay_sd_days: float | None = None,
    runs: int = 2000,
    seed: int | None = None,
    sample_invoice_delays: bool | None = None,
    inflow_adjustments: tuple[float, ...] | list[float] | None = None,
    outflow_adjustments: tuple[float, ...] | list[float] | None = None,
) -> MonteCarloResult:
    """Simulate weekly closing cash; optional cash series are plan-modified flows.

    Open receivables are sampled per customer from paid-invoice history (five
    observations) or a non-negative normal delay. Inflow amounts receive the
    editable sales-variability multiplier. This deliberately models receipt
    amount volatility as a sales proxy when invoice amounts are already fixed.
    """
    if runs < 1:
        raise ValueError("runs must be positive")
    projection = projection or forecast(case)
    horizon = len(projection.forecast_weeks)
    base_in = np.asarray([w.inflow for w in projection.forecast_weeks], dtype=float)
    base_out = np.asarray([w.outflow for w in projection.forecast_weeks], dtype=float)
    if inflows is not None:
        base_in = np.asarray(inflows, dtype=float)
    if outflows is not None:
        base_out = np.asarray(outflows, dtype=float)
    inflow_delta = np.asarray(inflow_adjustments if inflow_adjustments is not None else np.zeros(horizon), dtype=float)
    outflow_delta = np.asarray(outflow_adjustments if outflow_adjustments is not None else np.zeros(horizon), dtype=float)
    adjustments = np.asarray(balance_adjustments if balance_adjustments is not None else np.zeros(horizon), dtype=float)
    if any(array.shape != (horizon,) for array in (base_in, base_out, adjustments, inflow_delta, outflow_delta)):
        raise ValueError("Cash-flow series must match the forecast horizon")
    if not np.isfinite(base_in).all() or not np.isfinite(base_out).all() or not np.isfinite(adjustments).all():
        raise ValueError("Cash-flow series must contain finite values")
    cv = case.assumptions.sales_variability_cv if sales_variability_cv is None else float(sales_variability_cv)
    delay_sd = case.assumptions.customer_delay_sd_days if customer_delay_sd_days is None else float(customer_delay_sd_days)
    if cv < 0 or delay_sd < 0:
        raise ValueError("Variability and delay standard deviation cannot be negative")
    seed = case.assumptions.random_seed if seed is None else int(seed)
    rng = np.random.default_rng(seed)
    first_week = projection.forecast_weeks[0].week_start
    opening = projection.opening_cash if opening_cash is None else float(opening_cash)
    reserve_value = projection.reserve if reserve is None else float(reserve)

    # Retain recurring / run-rate receipts, while re-bucketing invoice events.
    sample_invoice_delays = inflows is None if sample_invoice_delays is None else sample_invoice_delays
    deterministic_invoice_by_week = np.zeros(horizon, dtype=float)
    customers = {c.customer_id: c for c in case.profile.customers}
    observed: dict[str, list[float]] = {key: [] for key in customers}
    for invoice in case.receivables:
        if invoice.paid_date and invoice.paid_amount >= invoice.amount:
            observed.setdefault(invoice.customer_id, []).append(float(max(0, (invoice.paid_date-invoice.due_date).days)))
    invoice_rows = []
    for invoice in case.receivables:
        amount = max(0.0, float(invoice.amount - invoice.paid_amount))
        if amount <= 0:
            continue
        delays = observed.get(invoice.customer_id, [])
        profile_delay = customers.get(invoice.customer_id).typical_delay_days if invoice.customer_id in customers else 0
        mean_delay = float(np.median(delays)) if len(delays) >= 3 else float(profile_delay)
        invoice_rows.append((invoice.customer_id, invoice.due_date, amount, mean_delay, delays))
        expected = invoice.due_date + timedelta(days=mean_delay)
        index = max(0, (expected - first_week).days // 7)
        if index < horizon:
            deterministic_invoice_by_week[index] += amount

    # Build paths in arrays; use per-invoice delay draws, grouped by customer.
    paths = np.empty((runs, horizon), dtype=np.float64)
    base_noninvoice = base_in - deterministic_invoice_by_week
    paths[:] = (np.maximum(base_noninvoice, 0.0) if sample_invoice_delays else base_in)[None, :]
    for customer_id, due_date, amount, mean_delay, history in invoice_rows if sample_invoice_delays else ():
        if len(history) >= 5:
            sampled = rng.choice(np.asarray(history, dtype=float), size=runs)
        else:
            sampled = np.maximum(0.0, rng.normal(mean_delay, delay_sd, size=runs))
        indices = np.floor((due_date + timedelta(days=0) - first_week).days / 7 + sampled / 7).astype(int)
        indices = np.maximum(indices, 0)
        valid = indices < horizon
        paths[np.flatnonzero(valid), indices[valid]] += amount

    # Log-normal multiplier has mean 1 and the configured coefficient of variation.
    if cv:
        sigma = float(np.sqrt(np.log1p(cv * cv)))
        paths *= rng.lognormal(-0.5 * sigma * sigma, sigma, size=(runs, horizon))
    paths += inflow_delta[None, :]
    paths -= (base_out + outflow_delta)[None, :]
    paths += adjustments[None, :]
    paths = np.cumsum(paths, axis=1)
    paths += opening
    week_starts = tuple(w.week_start for w in projection.forecast_weeks)
    below_reserve = paths < reserve_value
    return MonteCarloResult(
        week_starts, tuple(np.percentile(paths, 10, axis=0).tolist()),
        tuple(np.percentile(paths, 50, axis=0).tolist()), tuple(np.percentile(paths, 90, axis=0).tolist()),
        tuple(below_reserve.mean(axis=0).tolist()), tuple((paths < 0).mean(axis=0).tolist()),
        float(below_reserve.any(axis=1).mean()), runs, seed,
    )
