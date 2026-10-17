"""Load and validate a synthetic case from disk."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from .schema import Assumptions, BusinessProfile, Payable, Receivable, Transaction


@dataclass(frozen=True)
class SyntheticCase:
    transactions: list[Transaction]
    receivables: list[Receivable]
    payables: list[Payable]
    profile: BusinessProfile
    expected: dict[str, object]
    assumptions: Assumptions


def _read_csv(path: Path, model):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return [model.model_validate({key: value or None for key, value in row.items()}) for row in rows]


def load_case(case: str, root: str | Path | None = None) -> SyntheticCase:
    """Load a named case and validate every record with Pydantic."""
    base = Path(root) if root else Path(__file__).resolve().parents[1] / "data" / "synthetic"
    folder = base / case
    if not folder.is_dir():
        raise FileNotFoundError(f"Synthetic case not found: {case}")
    profile_raw = json.loads((folder / "profile.json").read_text(encoding="utf-8"))
    expected = json.loads((folder / "expected.json").read_text(encoding="utf-8"))
    assumptions_raw = profile_raw.pop("assumptions", {})
    return SyntheticCase(
        transactions=_read_csv(folder / "transactions.csv", Transaction),
        receivables=_read_csv(folder / "receivables.csv", Receivable),
        payables=_read_csv(folder / "payables.csv", Payable),
        profile=BusinessProfile.model_validate(profile_raw),
        expected=expected,
        assumptions=Assumptions.model_validate(assumptions_raw),
    )
