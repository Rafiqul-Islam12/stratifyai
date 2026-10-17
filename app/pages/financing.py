"""Financing - illustrative templates, cost and repayment capacity. Built in T06."""
from __future__ import annotations

import streamlit as st

from app import charts
from app import components as ui

ui.load_styles()

ui.page_header(
    "Financing",
    "Compare illustrative financing options and what the repayment would cost.",
    business="Demo business",
)

ui.alert_banner("warning", "Illustrative terms", "Not a real lender offer.")

ui.kpi_row(
    [
        ("Amount needed", "BDT 240,000", "Remaining funding gap."),
        ("Repayment capacity", "1.31x", "Average weekly net cash flow versus debt service."),
        ("Total cost", "BDT 18,900", "Interest plus fees for the selected option."),
        ("Tenor", "6 months", "Equal monthly instalments."),
    ]
)

st.caption("Sample data for layout review only - illustrative terms only.")

labels = ["Interest", "Fees", "Late fees"]
amounts = [14200, 4700, 0]
fig = charts.base_layout(title="Cost breakdown (placeholder data)", height=320)
fig.add_bar(
    x=labels,
    y=amounts,
    name="BDT",
    marker_color=[charts.PRIMARY, charts.BORDER, charts.SHORTAGE_FILL],
)
fig.update_yaxes(title_text="BDT")
fig.update_layout(showlegend=False)
st.plotly_chart(fig, use_container_width=True)

ui.section_title("Financing")
ui.empty_state(
    "Financing module lands in T06",
    "Term loan, invoice financing, supplier credit and credit line with editable terms and a schedule.",
    "Load demo business",
    disabled=True,
)

ui.footer()
