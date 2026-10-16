"""Smoke tests: the repository imports and the launcher answers.

These stay green for the whole project - every later task adds its own module
tests rather than widening these.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_version_is_supported() -> None:
    assert sys.version_info >= (3, 11), "StratifyAI requires Python 3.11 or newer"


def test_expected_top_level_layout_exists() -> None:
    required = ["core", "services", "app", "app/pages", "data", "tests", "scripts",
                "evidence", "static/fonts", "docs", ".streamlit"]
    missing = [name for name in required if not (ROOT / name).is_dir()]
    assert not missing, f"missing folders: {missing}"


def test_entry_point_is_a_file() -> None:
    assert (ROOT / "run.py").is_file()
    assert (ROOT / "app" / "main.py").is_file()
    assert (ROOT / "requirements.txt").is_file()
    assert (ROOT / ".env.example").is_file()


def test_env_file_is_ignored_by_git() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    entries = {line.strip() for line in gitignore.splitlines() if line.strip() and not line.startswith("#")}
    assert ".env" in entries


def test_streamlit_is_importable() -> None:
    import streamlit

    assert streamlit.__version__ >= "1.45", "streamlit >= 1.45 needed for self-hosted fonts"


def test_runner_help_exits_cleanly() -> None:
    result = subprocess.run([sys.executable, "run.py", "--help"],
                            check=False, capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0
    assert "StratifyAI launcher" in result.stdout
    assert "demo" in result.stdout and "status" in result.stdout


def test_runner_unknown_command_shows_usage() -> None:
    result = subprocess.run([sys.executable, "run.py", "nonsense"],
                            check=False, capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 2
    assert "StratifyAI launcher" in result.stdout


def test_runner_status_no_tests_runs() -> None:
    result = subprocess.run([sys.executable, "run.py", "status", "--no-tests"],
                            check=False, capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0
    assert "Tasks" in result.stdout
    assert "Progress" in result.stdout


def test_check_secrets_is_clean() -> None:
    result = subprocess.run([sys.executable, "scripts/check_secrets.py"],
                            check=False, capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
