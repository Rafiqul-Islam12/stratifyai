"""Generate deterministic, labelled synthetic SME cash-flow cases."""

import argparse
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

CASES = (
    "stable_healthy",
    "delayed_customer_payments",
    "high_expense_shortage",
    "import_financing",
    "sales_drop_cost_rise",
)
BASE_SEED = 20261018
START_DATE = date(2025, 10, 20)
WEEKS = 39
CUSTOMER_COUNT = 10
SUPPLIER_COUNT = 6


def _write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def generate_case(case: str, output_dir: Path, seed: int = BASE_SEED) -> Path:
    """Generate one case folder and return its path."""
    if case not in CASES:
        raise ValueError(f"Unknown case: {case}")
    index = CASES.index(case)
    rng = random.Random(seed + index * 101)
    folder = output_dir / case
    folder.mkdir(parents=True, exist_ok=True)

    scenario = {
        "stable_healthy": {"cash": 1_800_000, "sales": 280_000, "cost": 190_000, "delay": 8, "ramp": 1.0},
        "delayed_customer_payments": {"cash": 1_000_000, "sales": 260_000, "cost": 205_000, "delay": 48, "ramp": 1.0},
        "high_expense_shortage": {"cash": 480_000, "sales": 245_000, "cost": 310_000, "delay": 15, "ramp": 1.0},
        "import_financing": {"cash": 900_000, "sales": 260_000, "cost": 215_000, "delay": 17, "ramp": 1.0},
        "sales_drop_cost_rise": {"cash": 800_000, "sales": 275_000, "cost": 210_000, "delay": 16, "ramp": 0.66},
    }[case]
    customers = [
        {"customer_id": f"C{i:02d}", "name": f"Synthetic Customer {i:02d}",
         "typical_delay_days": max(0, scenario["delay"] + rng.randint(-8, 12))}
        for i in range(1, CUSTOMER_COUNT + 1)
    ]
    suppliers = [
        {"supplier_id": f"S{i:02d}", "name": f"Synthetic Supplier {i:02d}"}
        for i in range(1, SUPPLIER_COUNT + 1)
    ]

    receivables: list[dict] = []
    payables: list[dict] = []
    transactions: list[dict] = []
    cash = float(scenario["cash"])
    base_sales = float(scenario["sales"])
    base_cost = float(scenario["cost"])
    last_weeks = 12
    for week in range(WEEKS):
        week_date = START_DATE + timedelta(weeks=week)
        ramp = scenario["ramp"] if case == "sales_drop_cost_rise" and week >= WEEKS - 10 else 1.0
        cost_ramp = 1.25 if case == "sales_drop_cost_rise" and week >= WEEKS - 10 else 1.0
        sales = round(base_sales * ramp * rng.uniform(0.86, 1.14), 2)
        expense = round(base_cost * cost_ramp * rng.uniform(0.91, 1.11), 2)
        tx_date = week_date + timedelta(days=2)
        cash += sales
        transactions.extend((
            {"transaction_id": f"TX-{week + 1:03d}-IN", "date": tx_date.isoformat(),
             "description": "Synthetic weekly sales receipts", "category": "Sales", "amount": sales,
             "direction": "inflow", "balance_after": round(cash, 2)},
        ))
        cash -= expense
        transactions.append(
            {"transaction_id": f"TX-{week + 1:03d}-OUT", "date": (tx_date + timedelta(days=1)).isoformat(),
             "description": "Synthetic operating expenses", "category": "Operating expense", "amount": expense,
             "direction": "outflow", "balance_after": round(cash, 2)}
        )
        if week >= WEEKS - last_weeks:
            customer = customers[(week - (WEEKS - last_weeks)) % CUSTOMER_COUNT]
            supplier = suppliers[(week - (WEEKS - last_weeks)) % SUPPLIER_COUNT]
            invoice_amount = round(sales * rng.uniform(0.72, 1.02), 2)
            invoice_due = tx_date + timedelta(days=30)
            paid = (week < WEEKS - 2 and rng.random() > (0.75 if case == "delayed_customer_payments" else 0.2))
            paid_date = invoice_due + timedelta(days=customer["typical_delay_days"]) if paid else None
            receivables.append({"invoice_id": f"INV-{week + 1:03d}", "customer_id": customer["customer_id"],
                                "issue_date": tx_date.isoformat(), "due_date": invoice_due.isoformat(),
                                "amount": invoice_amount, "paid_date": paid_date.isoformat() if paid_date else "",
                                "paid_amount": invoice_amount if paid else 0})
            bill_amount = round(expense * rng.uniform(0.56, 0.88), 2)
            bill_due = tx_date + timedelta(days=21)
            bill_paid = week < WEEKS - 1 and rng.random() > 0.12
            payable_category = "Discretionary marketing" if week % 4 == 0 else "Inventory"
            payables.append({"bill_id": f"BILL-{week + 1:03d}", "supplier_id": supplier["supplier_id"],
                             "issue_date": tx_date.isoformat(), "due_date": bill_due.isoformat(),
                             "amount": bill_amount, "paid_date": (bill_due + timedelta(days=2)).isoformat() if bill_paid else "",
                             "paid_amount": bill_amount if bill_paid else 0, "deferrable": week % 3 == 0,
                             "discretionary": payable_category.startswith("Discretionary"), "category": payable_category})

    import_fields = {}
    if case == "import_financing":
        import_fields = {"product_cost": 1_250_000, "deposit_pct": 30, "shipping_cost": 180_000,
                         "fx_rate_bdt_per_usd": 122.0, "lead_time_weeks": 8, "sales_ramp_weeks": 10}
    profile = {
        "business_id": f"SYN-{index + 1:02d}", "business_name": f"Synthetic SME Case {index + 1}",
        "industry": "Synthetic wholesale and distribution", "currency": "BDT",
        "opening_cash": scenario["cash"], "customers": customers, "suppliers": suppliers,
        "import_scenario": import_fields,
        "assumptions": {"currency": "BDT", "forecast_horizon_weeks": 13,
                        "minimum_reserve_weeks": 2, "funding_buffer_pct": 0,
                        "collection_pct": 50, "collection_weeks": 2,
                        "collection_haircut_pct": 0, "deferral_weeks": 2,
                        "late_fee_pct": 0, "discretionary_reduction_pct": 10,
                        "discretionary_start_week": 1, "sales_variability_cv": 0.15,
                        "customer_delay_sd_days": 7, "random_seed": seed + index * 101},
    }
    shortage = case != "stable_healthy"
    expected = {"shortage_expected": shortage,
                "approximate_shortage_week_range": [1, 6] if case == "high_expense_shortage" else ([4, 10] if shortage else None),
                "note": "Qualitative synthetic scenario expectation; validate with the forecast engine."}
    _write_csv(folder / "transactions.csv", transactions)
    _write_csv(folder / "receivables.csv", receivables)
    _write_csv(folder / "payables.csv", payables)
    for filename, payload in (("profile.json", profile), ("expected.json", expected)):
        (folder / filename).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (folder / "README.md").write_text("SYNTHETIC DATA — deterministic demonstration records; not real businesses or people.\n", encoding="utf-8")
    return folder


def generate_all(output_dir: Path | None = None, seed: int = BASE_SEED) -> list[Path]:
    """Generate all five cases beneath data/synthetic by default."""
    target = output_dir or Path(__file__).resolve().parent / "synthetic"
    return [generate_case(case, target, seed) for case in CASES]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=BASE_SEED)
    args = parser.parse_args()
    for path in generate_all(args.output_dir, args.seed):
        print(f"Generated {path}")
