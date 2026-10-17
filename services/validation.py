"""Safe CSV/XLSX validation for user supplied financial tables."""

from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_ROWS = 50_000
MAX_TEXT_LENGTH = 500

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "transactions": ("transaction_id", "date", "description", "category", "amount", "direction", "balance_after"),
    "receivables": ("invoice_id", "customer_id", "issue_date", "due_date", "amount"),
    "payables": ("bill_id", "supplier_id", "issue_date", "due_date", "amount", "category"),
}
ID_COLUMNS = {"transactions": "transaction_id", "receivables": "invoice_id", "payables": "bill_id"}
DATE_COLUMNS = {"date", "issue_date", "due_date", "paid_date"}


@dataclass(frozen=True)
class ValidationIssue:
    message: str
    severity: str = "error"
    row: int | None = None
    column: str | None = None


@dataclass
class ValidationReport:
    kind: str
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    cleaned_data: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return bool(self.cleaned_data) and not self.errors


def template_csv(kind: str) -> bytes:
    """Return a header-only CSV template for a supported data type."""
    if kind not in REQUIRED_COLUMNS:
        raise ValueError(f"Unknown data type: {kind}")
    columns = list(REQUIRED_COLUMNS[kind])
    if kind == "receivables":
        columns += ["paid_date", "paid_amount"]
    elif kind == "payables":
        columns += ["paid_date", "paid_amount", "deferrable", "discretionary"]
    return (",".join(columns) + "\n").encode("utf-8")


def _parse_csv(content: bytes) -> tuple[list[str], list[list[Any]]]:
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        headers = next(reader)
    except StopIteration:
        return [], []
    rows = list(reader)
    return [str(value).strip() for value in headers], rows


def _parse_xlsx(content: bytes) -> tuple[list[str], list[list[Any]]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("Excel support is unavailable; install the project's openpyxl dependency.") from exc
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
    try:
        sheet = workbook.active
        iterator = sheet.iter_rows(values_only=True)
        first = next(iterator, ())
        headers = [str(value).strip() if value is not None else "" for value in first]
        rows = [list(values) for values in iterator]
        return headers, rows
    finally:
        workbook.close()


def _kind_from_headers(headers: list[str]) -> str:
    values = set(headers)
    for kind, id_column in ID_COLUMNS.items():
        if id_column in values:
            return kind
    return "unknown"


def _cell_text(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    raise ValueError("Use an ISO date such as 2026-10-18.")


def _parse_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Expected a numeric amount.")
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValueError("Expected a numeric amount.") from None
    if not number.is_finite():
        raise ValueError("Amount must be a finite number.")
    return float(number)


def _looks_formula(value: str) -> bool:
    return bool(value) and value[0] in "=+-@"


def _safe_text(value: str) -> str:
    return "'" + value if _looks_formula(value) else value


def validate_upload(
    filename: str,
    content: bytes,
    *,
    kind: str = "auto",
    max_bytes: int = MAX_UPLOAD_BYTES,
    max_rows: int = MAX_ROWS,
    today: date | None = None,
) -> ValidationReport:
    """Parse and validate one CSV or XLSX file without executing cell content.

    All parsed rows are retained in ``cleaned_data``. Invalid rows are listed
    with source row numbers; callers should only use the dataset when valid.
    """
    suffix = Path(filename).suffix.lower()
    report = ValidationReport(kind=kind)
    report.stats["file_bytes"] = len(content)
    if suffix not in {".csv", ".xlsx"}:
        report.errors.append(ValidationIssue("Unsupported file type. Upload CSV or XLSX."))
        return report
    if len(content) > max_bytes:
        report.errors.append(ValidationIssue(f"File exceeds the {max_bytes // (1024 * 1024)} MB size limit."))
        return report
    try:
        headers, raw_rows = _parse_csv(content) if suffix == ".csv" else _parse_xlsx(content)
    except (UnicodeDecodeError, csv.Error, RuntimeError, OSError, ValueError) as exc:
        report.errors.append(ValidationIssue(str(exc) if isinstance(exc, RuntimeError) else "Could not read the uploaded file."))
        return report
    if not headers or not any(headers):
        report.errors.append(ValidationIssue("The file must contain a header row."))
        return report
    if len(headers) != len(set(headers)):
        report.errors.append(ValidationIssue("Column names must be unique."))
    if any(not name for name in headers):
        report.errors.append(ValidationIssue("Column names cannot be blank."))
    data_kind = _kind_from_headers(headers) if kind == "auto" else kind
    report.kind = data_kind
    if data_kind not in REQUIRED_COLUMNS:
        report.errors.append(ValidationIssue("Could not identify the data type. Choose transactions, receivables, or payables."))
        report.stats.update(rows=len(raw_rows), valid_rows=0, invalid_rows=len(raw_rows), columns=len(headers))
        return report
    for required in REQUIRED_COLUMNS[data_kind]:
        if required not in headers:
            report.errors.append(ValidationIssue(f"Missing required column: {required}.", column=required))

    if len(raw_rows) > max_rows:
        report.errors.append(ValidationIssue(f"File has {len(raw_rows):,} rows; the maximum is {max_rows:,}."))
    truncated_rows = raw_rows[:max_rows]
    row_error_counts: dict[int, int] = {}

    def error(row_number: int, message: str, column: str | None = None) -> None:
        report.errors.append(ValidationIssue(message, row=row_number, column=column))
        row_error_counts[row_number] = row_error_counts.get(row_number, 0) + 1

    def warning(row_number: int, message: str, column: str | None = None) -> None:
        report.warnings.append(ValidationIssue(message, severity="warning", row=row_number, column=column))

    safe_rows: list[dict[str, Any]] = []
    exact_seen: dict[tuple[tuple[str, str], ...], int] = {}
    id_rows: dict[str, list[int]] = {}
    currencies: dict[str, int] = {}
    reference_day = today or date.today()
    numeric_columns = {header for header in headers if header == "amount" or header.endswith("_amount") or header == "balance_after"}
    date_columns = {header for header in headers if header in DATE_COLUMNS or header.endswith("_date")}

    for index, raw_row in enumerate(truncated_rows, start=2):
        if len(raw_row) > len(headers):
            error(index, "Row contains more values than the header; extra cells were retained.")
        row: dict[str, Any] = {}
        for col_index, column in enumerate(headers):
            value = raw_row[col_index] if col_index < len(raw_row) else None
            text_value = _cell_text(value).strip()
            if len(text_value) > MAX_TEXT_LENGTH:
                error(index, f"Text exceeds the {MAX_TEXT_LENGTH}-character limit.", column)
            if value is None or text_value == "":
                row[column] = None
                if column in REQUIRED_COLUMNS[data_kind]:
                    error(index, "Required value is missing.", column)
                continue
            if column in numeric_columns:
                try:
                    number = _parse_number(value)
                    row[column] = number
                    if (column == "amount" or column.endswith("_amount")) and number < 0:
                        error(index, "Amount cannot be negative.", column)
                except ValueError as exc:
                    row[column] = _safe_text(text_value)
                    if _looks_formula(text_value):
                        warning(index, "Formula-like content was neutralised.", column)
                    error(index, str(exc), column)
                continue
            if column in date_columns:
                try:
                    parsed = _parse_date(value)
                    row[column] = parsed.isoformat() if parsed else None
                    if parsed:
                        if parsed > reference_day + timedelta(days=365):
                            warning(index, "Date is more than one year in the future.", column)
                        if parsed < reference_day - timedelta(days=365 * 10):
                            warning(index, "Date is more than ten years old.", column)
                except ValueError as exc:
                    row[column] = _safe_text(text_value)
                    error(index, str(exc), column)
                continue
            if column == "direction":
                direction = text_value.lower()
                row[column] = _safe_text(direction)
                if direction not in {"inflow", "outflow"}:
                    error(index, "Transaction type must be inflow or outflow.", column)
                if row[column] != direction:
                    warning(index, "Formula-like content was neutralised.", column)
                continue
            safe_value = _safe_text(text_value)
            row[column] = safe_value
            if safe_value != text_value:
                warning(index, "Formula-like content was neutralised.", column)
        if len(raw_row) > len(headers):
            row["__extra_cells__"] = [_safe_text(_cell_text(value)) for value in raw_row[len(headers):]]

        if "currency" in row:
            currency = str(row["currency"] or "").strip().upper()
            if not currency:
                error(index, "Currency value is missing.", "currency")
            else:
                currencies[currency] = currencies.get(currency, 0) + 1
        exact_key = tuple(sorted((key, repr(value)) for key, value in row.items()))
        if exact_key in exact_seen:
            error(index, f"Exact duplicate of row {exact_seen[exact_key]}.")
        else:
            exact_seen[exact_key] = index
        id_column = ID_COLUMNS[data_kind]
        identifier = row.get(id_column)
        if identifier is not None:
            id_rows.setdefault(str(identifier), []).append(index)
        safe_rows.append(row)

    for identifier, rows in id_rows.items():
        if len(rows) > 1:
            for row_number in rows:
                error(row_number, f"Duplicate {ID_COLUMNS[data_kind]}: {identifier}.", ID_COLUMNS[data_kind])
    if len(currencies) > 1:
        for row_number in range(2, len(safe_rows) + 2):
            error(row_number, "Currency values are inconsistent.", "currency")
    elif currencies and "BDT" not in currencies:
        warning(2, "Currency is not BDT; confirm the amount units before use.", "currency")

    for row_number in range(max_rows + 2, len(raw_rows) + 2):
        error(row_number, f"Row exceeds the {max_rows:,}-row limit and was not processed.")

    report.cleaned_data = safe_rows
    invalid_rows = len(row_error_counts)
    invalid_processed_rows = sum(1 for row_number in row_error_counts if row_number <= len(truncated_rows) + 1)
    report.stats.update(
        rows=len(raw_rows),
        checked_rows=len(safe_rows),
        valid_rows=max(0, len(safe_rows) - invalid_processed_rows),
        invalid_rows=invalid_rows,
        columns=len(headers),
        currencies=sorted(currencies),
    )
    return report
