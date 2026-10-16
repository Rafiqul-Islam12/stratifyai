#!/usr/bin/env python3
"""StratifyAI entry point.

Scaffold only (T01): page configuration, title and a data-free placeholder.
T02 replaces this with the navigation, sidebar and page shell.
"""
import streamlit as st

TITLE = "StratifyAI"
TAGLINE = "The Liquidity Decision Lab for SME Financial Intelligence"


def main() -> None:
    st.set_page_config(layout="wide", page_title=TITLE)
    st.title(TITLE)
    st.caption(TAGLINE)
    st.info("Scaffold only - feature pages are built by tasks T02 to T18. See docs/PLAN.md.")
    st.caption("Synthetic data, not financial advice.")


main()
