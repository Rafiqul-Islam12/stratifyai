"""Schema, loader, and determinism tests for generated synthetic cases."""

import hashlib
from pathlib import Path

import pytest

from core.loaders import load_case
from data.generate_synthetic import CASES, generate_all


def _hash_tree(folder: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(folder).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


@pytest.fixture(scope="module")
def generated_cases(tmp_path_factory):
    root = tmp_path_factory.mktemp("synthetic")
    generate_all(root)
    return root


@pytest.mark.parametrize("case", CASES)
def test_case_has_valid_records_and_synthetic_label(generated_cases, case):
    loaded = load_case(case, generated_cases)
    assert len(loaded.transactions) >= 26 * 2
    assert len(loaded.receivables) == 12
    assert len(loaded.payables) == 12
    assert len(loaded.profile.customers) == 10
    assert len(loaded.profile.suppliers) == 6
    assert loaded.profile.currency == "BDT"
    assert "SYNTHETIC DATA" in (generated_cases / case / "README.md").read_text(encoding="utf-8")


def test_generator_is_deterministic(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    generate_all(first)
    generate_all(second)
    for case in CASES:
        assert _hash_tree(first / case) == _hash_tree(second / case)


def test_import_case_has_import_assumptions(generated_cases):
    profile = load_case("import_financing", generated_cases).profile
    assert profile.import_scenario["lead_time_weeks"] == 8
    assert profile.import_scenario["fx_rate_bdt_per_usd"] > 0
