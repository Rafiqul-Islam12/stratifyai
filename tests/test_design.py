"""Design-system smoke tests (T02).

Streamlit is absent on a machine without the venv, so the import that needs it
is guarded: it skips rather than erroring.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
STYLES = APP / "styles.css"
CONFIG = ROOT / ".streamlit" / "config.toml"

# Pages and the shell must take colour from tokens in styles.css / charts.py.
# A literal colour anywhere here is a token that got copy-pasted in.
OUT_OF_PLACE = [APP / "main.py", *sorted(APP.glob("pages/*.py"))]

HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
URL_HOST = re.compile(r"(https?://)([^\s'\")>]*)")


def test_design_files_exist() -> None:
    assert STYLES.is_file()
    assert CONFIG.is_file()
    assert (APP / "components.py").is_file()
    assert (APP / "charts.py").is_file()
    assert (APP / "main.py").is_file()


def test_style_sheet_is_under_line_budget() -> None:
    """The v2 design system (docs/UI_REDESIGN.md) replaced the 150-line T02 budget."""
    lines = STYLES.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 700, f"styles.css has {len(lines)} lines, budget is about 600"


def test_shared_typography_and_cards_wrap_without_truncation() -> None:
    styles = STYLES.read_text(encoding="utf-8")
    assert ".sa-header {" in styles and "align-items: center" in styles
    assert ".sa-kpi-title { min-height: 2.7em; line-height: 1.35; }" in styles
    kpi_rules = re.search(r"\.sa-kpi-value\s*\{([^}]+)\}", styles)
    assert kpi_rules is not None
    assert "overflow-wrap: anywhere" in kpi_rules.group(1)
    assert "white-space: normal" in kpi_rules.group(1)
    assert "text-overflow" not in kpi_rules.group(1)
    plan_value_rules = re.search(r"\.sa-plan-row span:last-child\s*\{([^}]+)\}", styles)
    assert plan_value_rules is not None
    assert "text-align: right" in plan_value_rules.group(1)
    assert "overflow-wrap: anywhere" in plan_value_rules.group(1)


def test_no_hardcoded_colours_outside_tokens() -> None:
    """Colour literals belong in styles.css and charts.py, not in the pages."""
    violations: dict[str, list[str]] = {}
    for path in OUT_OF_PLACE:
        if not path.is_file():
            continue
        found = HEX.findall(path.read_text(encoding="utf-8"))
        if found:
            violations[path.relative_to(ROOT).as_posix()] = sorted(set(found))
    assert not violations, f"hard-coded colours outside tokens: {violations}"


def test_no_external_url_in_the_app() -> None:
    """The demo must work offline, so the app may reference no external host.

    Loopback addresses are fine - that is where Streamlit itself listens.
    """
    offenders: list[str] = []
    for path in [APP / "main.py", APP / "components.py", APP / "charts.py", STYLES, CONFIG, *(APP.glob("pages/*.py"))]:
        if not path.is_file():
            continue
        hosts = set()
        for scheme, host in URL_HOST.findall(path.read_text(encoding="utf-8").lower()):
            host = host.split("/")[0].split(")")[0].split(";")[0].strip(" ,")
            if host == "www.w3.org":  # the SVG XML namespace identifier inside inline SVG; the browser never requests it
                continue
            if host and host not in {"127.0.0.1", "localhost"} and not host.startswith("127."):
                hosts.add(f"{scheme}://{host}")
        if hosts:
            offenders.append(f"{path.relative_to(ROOT).as_posix()}: {sorted(hosts)}")
    assert not offenders, f"external URL references in the app: {offenders}"


def test_charts_module_imports_without_streamlit() -> None:
    charts = importlib.import_module("app.charts")
    assert charts.LAYER_STYLES["ACTUAL"]["dash"] == "solid"
    assert charts.LAYER_STYLES["FORECAST"]["dash"] == "dash"


def test_components_load_when_streamlit_is_present() -> None:
    if importlib.util.find_spec("streamlit") is None:
        import pytest

        pytest.skip("streamlit is not installed")
    importlib.import_module("app.components")


def test_styles_are_reinjected_after_a_streamlit_rerun() -> None:
    if importlib.util.find_spec("streamlit") is None:
        import pytest

        pytest.skip("streamlit is not installed")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "pages" / "overview.py"))
    at.session_state["_sa_styles"] = True  # Stale session state from a prior run must not suppress CSS.
    at.run()
    assert any("--fs-caption" in element.value for element in at.markdown)


def test_design_tokens_are_green_and_off_white() -> None:
    styles = STYLES.read_text(encoding="utf-8")
    for token in ("--green-900:", "--green-700:", "--cream-50:", "--cream-100:", "--amber:", "--fs-caption:", "--fs-kpi:", "--fs-hero:"):
        assert token in styles, token
    assert "#4F46E5" not in styles  # the old indigo brand colour must be gone


def test_shell_defines_fixed_navbar_and_fixed_sidebar() -> None:
    styles = STYLES.read_text(encoding="utf-8")
    assert ".st-key-sa-navbar" in styles and "position: fixed" in styles
    assert "stSidebarCollapseButton" in styles  # the sidebar is always open


def test_icons_module_has_no_external_assets() -> None:
    icons = importlib.import_module("app.icons")
    assert icons.svg("lock").startswith("<svg") and "http" not in icons.svg("lock") and "http" not in icons.logo_mark()
