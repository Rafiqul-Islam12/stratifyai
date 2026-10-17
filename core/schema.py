"""Typed schemas for synthetic SME cash-flow data."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Transaction(StrictModel):
    transaction_id: str
    date: date
    description: str
    category: str
    amount: float
    direction: Literal["inflow", "outflow"]
    balance_after: float


class Receivable(StrictModel):
    invoice_id: str
    customer_id: str
    issue_date: date
    due_date: date
    amount: float = Field(gt=0)
    paid_date: date | None = None
    paid_amount: float = Field(default=0, ge=0)


class Payable(StrictModel):
    bill_id: str
    supplier_id: str
    issue_date: date
    due_date: date
    amount: float = Field(gt=0)
    paid_date: date | None = None
    paid_amount: float = Field(default=0, ge=0)
    deferrable: bool = False
    discretionary: bool = False
    category: str


class Customer(StrictModel):
    customer_id: str
    name: str
    typical_delay_days: int = Field(ge=0)


class Supplier(StrictModel):
    supplier_id: str
    name: str


class BusinessProfile(StrictModel):
    business_id: str
    business_name: str
    industry: str
    currency: str = "BDT"
    opening_cash: float = Field(ge=0)
    customers: list[Customer]
    suppliers: list[Supplier]
    import_scenario: dict[str, float | int | str] = Field(default_factory=dict)


class Assumptions(StrictModel):
    currency: str = "BDT"
    forecast_horizon_weeks: int = Field(default=13, ge=8)
    minimum_reserve_weeks: float = Field(default=2, ge=0)
    funding_buffer_pct: float = Field(default=0, ge=0)
    collection_pct: float = Field(default=50, ge=0, le=100)
    collection_weeks: int = Field(default=2, ge=1)
    collection_haircut_pct: float = Field(default=0, ge=0, le=100)
    deferral_weeks: int = Field(default=2, ge=1)
    late_fee_pct: float = Field(default=0, ge=0)
    discretionary_reduction_pct: float = Field(default=10, ge=0, le=100)
    discretionary_start_week: int = Field(default=1, ge=1)
    sales_variability_cv: float = Field(default=0.15, ge=0)
    customer_delay_sd_days: float = Field(default=7, ge=0)
    random_seed: int = 42
