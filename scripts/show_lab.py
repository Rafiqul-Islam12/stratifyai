"""Print a compact deterministic Decision Lab comparison for synthetic case 3."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.financing import funding_amount
from core.forecast import forecast
from core.lab import run_lab
from core.loaders import load_case


def main() -> None:
    case = load_case("high_expense_shortage")
    result = run_lab(case)
    original_gap = forecast(case).funding_gap
    print(f"Decision Lab comparison: {case.profile.business_name} (case 3)")
    print(f"Original deterministic funding gap: BDT {original_gap:,.0f}")
    print("Plan        Gap before finance   Facility amount   Remaining gap   Feasible")
    for name in ("Option 0", "L1", "L2", "L3", "Option A", "Option B", "Option C"):
        plan = result.plans[name]
        print(f"{name:<11} BDT {plan.funding_gap:>12,.0f}   BDT {plan.financing_amount:>11,.0f}"
              f"   BDT {plan.remaining_gap:>11,.0f}   {plan.is_feasible}")
    expected_c = funding_amount(original_gap, "Term loan")
    print(f"Option C rounded facility check: BDT {result.plans['Option C'].financing_amount:,.0f} "
          f"(gap rounded up to BDT 1,000: BDT {expected_c:,.0f})")
    print(f"Option B facility <= C facility: "
          f"{result.plans['Option B'].financing_amount <= result.plans['Option C'].financing_amount}")
    assert result.plans["Option C"].financing_amount == expected_c
    assert result.plans["Option B"].financing_amount <= result.plans["Option C"].financing_amount
    print(f"Best plan: {result.best_plan_id} - {result.best_plan_reason}")
    print(f"Borrowing necessary: {result.borrowing_necessary} - {result.borrowing_reason}")


if __name__ == "__main__":
    main()
