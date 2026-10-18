"""Data Upload page: validate untrusted files before placing rows in session state."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app import components as ui
from core.loaders import load_case
from data.generate_synthetic import CASES
from services.actions import record_upload
from services.auth import current_user
from services.permissions import PermissionDenied
from services.validation import REQUIRED_COLUMNS, ValidationIssue, ValidationReport, template_csv, validate_upload

DEMO_LABELS = {
    "stable_healthy": "Stable and healthy",
    "delayed_customer_payments": "Delayed customer payments",
    "high_expense_shortage": "High expense, shortage",
    "import_financing": "Import financing",
    "sales_drop_cost_rise": "Sales drop, cost rise",
}
DATA_LABELS = {"transactions": "Transactions", "receivables": "Receivables / invoices", "payables": "Payables / bills"}

ui.load_styles()
active_case_name = st.session_state.get("active_synthetic_case")
active_case = st.session_state.get("synthetic_case_data")
business = active_case.profile.business_name if active_case else "Select a demo business"
ui.page_header(
    "Data Upload",
    "Validate transaction, invoice, and bill files before using their rows.",
    business=business,
    scenario=DEMO_LABELS.get(active_case_name, "Synthetic data") if active_case else "Synthetic data",
)
ui.alert_banner(
    "info",
    "Untrusted input",
    "File contents are treated only as data. Formula-like cells are neutralised and never executed.",
)

ui.section_title("Upload a file")
data_kind = st.selectbox(
    "Data type",
    options=["auto", *REQUIRED_COLUMNS],
    format_func=lambda value: "Detect from columns" if value == "auto" else DATA_LABELS[value],
)
template_kind = st.selectbox("Template type", options=list(REQUIRED_COLUMNS), format_func=lambda value: DATA_LABELS[value])
st.download_button(
    "Download CSV template",
    data=template_csv(template_kind),
    file_name=f"{template_kind}_template.csv",
    mime="text/csv",
)
uploaded = st.file_uploader(
    "Choose a CSV or Excel workbook",
    type=["csv", "xlsx"],
    help="Maximum file size is 5 MB and maximum row count is 50,000.",
)

if uploaded is not None:
    try:
        report: ValidationReport = validate_upload(uploaded.name, uploaded.getvalue(), kind=data_kind)
    except (OSError, ValueError, TypeError, RuntimeError):
        report = ValidationReport(kind=data_kind)
        report.errors.append(ValidationIssue("The file could not be processed. Check the file format and try again."))
    ui.section_title("Validation report")
    metrics = st.columns(4)
    metrics[0].metric("Rows found", f"{report.stats.get('rows', 0):,}")
    metrics[1].metric("Rows checked", f"{report.stats.get('checked_rows', 0):,}")
    metrics[2].metric("Valid rows", f"{report.stats.get('valid_rows', 0):,}")
    metrics[3].metric("Rows with errors", f"{report.stats.get('invalid_rows', 0):,}")
    st.caption(f"Detected data type: {DATA_LABELS.get(report.kind, 'Unknown')}")

    messages = [
        {"Severity": issue.severity.title(), "Row": issue.row or "File", "Column": issue.column or "—", "Message": issue.message}
        for issue in [*report.errors, *report.warnings]
    ]
    if report.errors:
        st.error(f"Found {len(report.errors):,} validation error(s). Correct them before using this dataset.")
    elif report.is_valid:
        st.success("All checked rows passed validation.")
    if report.warnings:
        st.warning(f"Found {len(report.warnings):,} warning(s). Review them before use.")
    if messages:
        st.dataframe(pd.DataFrame(messages), use_container_width=True, hide_index=True)

    if report.cleaned_data:
        ui.section_title("Preview (first 100 rows)")
        st.dataframe(pd.DataFrame(report.cleaned_data[:100]), use_container_width=True, hide_index=True)
    if st.button("Use this dataset", type="primary", disabled=not report.is_valid):
        try:
            user = current_user()
            if user:
                record_upload(user, uploaded.name, len(report.cleaned_data))
            st.session_state["uploaded_dataset"] = {
                "kind": report.kind,
                "filename": uploaded.name,
                "rows": report.cleaned_data,
                "stats": report.stats,
            }
            st.success(f"Validated {len(report.cleaned_data):,} rows and saved them for this session.")
        except PermissionDenied as exc:
            st.error(str(exc))
        except Exception:  # noqa: BLE001 - keep parser and storage details out of the UI
            st.error("The validated dataset could not be saved. The attempt was recorded safely.")

ui.section_title("Load a demo business")
demo_case = st.selectbox("Synthetic case", options=CASES, format_func=lambda value: DEMO_LABELS[value],
    index=CASES.index(active_case_name) if active_case_name in CASES else 0, key="upload-demo-case-select")
st.caption("Synthetic data · BDT · for demonstration only")
if st.button("Load demo business"):
    try:
        case_data = load_case(demo_case)
        st.session_state["active_synthetic_case"] = demo_case
        st.session_state["synthetic_case_data"] = case_data
        st.rerun()
    except (OSError, ValueError, KeyError):
        st.error("The selected demo data could not be loaded. Choose another synthetic case or retry.")

if active_case:
    st.success(
        f"Loaded {DEMO_LABELS.get(active_case_name, active_case_name)} · "
        f"{len(active_case.transactions):,} transactions · "
        f"{len(active_case.receivables):,} invoices · {len(active_case.payables):,} bills."
    )
if "uploaded_dataset" in st.session_state:
    saved = st.session_state["uploaded_dataset"]
    st.info(f"Session dataset: {saved['filename']} · {len(saved['rows']):,} validated {saved['kind']} rows.")

ui.footer()
