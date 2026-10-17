"""Upload validation rejects malformed data and neutralises formula-like text."""

import csv
import io
from datetime import date

from openpyxl import Workbook

from core.loaders import load_case
from data.generate_synthetic import CASES
from services.validation import REQUIRED_COLUMNS, validate_upload


def _csv_content(headers=None, rows=None):
    headers = headers or list(REQUIRED_COLUMNS["transactions"])
    rows = rows or [["T-1", "2026-10-01", "Sales", "Sales", "125.50", "inflow", "125.50"]]
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _transaction_row(**updates):
    row = {"transaction_id": "T-1", "date": "2026-10-01", "description": "Sales",
           "category": "Sales", "amount": "125.50", "direction": "inflow", "balance_after": "125.50"}
    row.update(updates)
    return [row[column] for column in REQUIRED_COLUMNS["transactions"]]


def test_missing_required_column_is_reported():
    headers = [column for column in REQUIRED_COLUMNS["transactions"] if column != "amount"]
    values = dict(zip(REQUIRED_COLUMNS["transactions"], _transaction_row()))
    row = [values[column] for column in headers]
    report = validate_upload("transactions.csv", _csv_content(headers, [row]))
    assert any(issue.column == "amount" and "Missing required column" in issue.message for issue in report.errors)
    assert not report.is_valid


def test_exact_and_same_id_duplicates_are_reported():
    first = _transaction_row()
    exact_copy = first.copy()
    same_id_different_record = _transaction_row(description="Different")
    report = validate_upload("transactions.csv", _csv_content(rows=[first, exact_copy, same_id_different_record]))
    messages = [issue.message for issue in report.errors]
    assert any("Exact duplicate" in message for message in messages)
    assert sum("Duplicate transaction_id" in message for message in messages) == 3
    assert report.stats["invalid_rows"] == 3


def test_bad_date_and_suspicious_dates_are_reported():
    rows = [
        _transaction_row(date="not-a-date"),
        _transaction_row(transaction_id="T-2", date="1990-01-01"),
        _transaction_row(transaction_id="T-3", date="2030-01-01"),
    ]
    report = validate_upload("transactions.csv", _csv_content(rows=rows), today=date(2026, 10, 18))
    assert any(issue.column == "date" and issue.severity == "error" for issue in report.errors)
    assert sum(issue.column == "date" for issue in report.warnings) == 2


def test_negative_and_text_amounts_are_rejected():
    rows = [_transaction_row(amount="-2"), _transaction_row(transaction_id="T-2", amount="many")]
    report = validate_upload("transactions.csv", _csv_content(rows=rows))
    assert any(issue.column == "amount" and "negative" in issue.message for issue in report.errors)
    assert any(issue.column == "amount" and "numeric" in issue.message for issue in report.errors)


def test_formula_like_cells_are_neutralised_and_reported():
    report = validate_upload("transactions.csv", _csv_content(rows=[_transaction_row(description="=1+1")]))
    assert report.cleaned_data[0]["description"] == "'=1+1"
    assert any("neutralised" in issue.message for issue in report.warnings)
    assert report.is_valid


def test_formula_in_amount_is_neutralised_but_invalid():
    report = validate_upload("transactions.csv", _csv_content(rows=[_transaction_row(amount="=1+1")]))
    assert report.cleaned_data[0]["amount"] == "'=1+1"
    assert any(issue.column == "amount" for issue in report.errors)


def test_oversized_file_is_rejected():
    report = validate_upload("transactions.csv", b"x" * 11, max_bytes=10)
    assert any("size limit" in issue.message for issue in report.errors)
    assert not report.cleaned_data


def test_wrong_transaction_type_is_rejected():
    report = validate_upload("transactions.csv", _csv_content(rows=[_transaction_row(direction="transfer")]))
    assert any(issue.column == "direction" and "inflow or outflow" in issue.message for issue in report.errors)


def test_row_limit_is_reported_without_silently_dropping_rows():
    report = validate_upload("transactions.csv", _csv_content(rows=[_transaction_row(), _transaction_row(transaction_id="T-2")]), max_rows=1)
    assert any("maximum is 1" in issue.message for issue in report.errors)
    assert len(report.cleaned_data) == 1
    assert report.stats["rows"] == 2


def test_inconsistent_currency_is_rejected():
    headers = list(REQUIRED_COLUMNS["transactions"]) + ["currency"]
    rows = [
        _transaction_row() + ["BDT"],
        _transaction_row(transaction_id="T-2") + ["USD"],
    ]
    report = validate_upload("transactions.csv", _csv_content(headers, rows))
    assert any(issue.column == "currency" and "inconsistent" in issue.message for issue in report.errors)


def test_xlsx_upload_is_supported():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(REQUIRED_COLUMNS["transactions"]))
    sheet.append(_transaction_row(description="=1+1"))
    content = io.BytesIO()
    workbook.save(content)
    report = validate_upload("transactions.xlsx", content.getvalue())
    assert report.is_valid
    assert report.cleaned_data[0]["description"] == "'=1+1"


def test_all_demo_cases_load_through_validated_loader():
    for case in CASES:
        loaded = load_case(case)
        assert loaded.transactions
        assert loaded.receivables
        assert loaded.payables
