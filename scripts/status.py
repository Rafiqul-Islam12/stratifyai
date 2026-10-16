#!/usr/bin/env python3
"""Project status: tasks done from docs/PLAN.md, current task from docs/PROGRESS.md,
recent commits, and an optional quick pytest run.

Usage: python scripts/status.py [--no-tests]
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "PLAN.md"
PROGRESS = ROOT / "docs" / "PROGRESS.md"

TASK_ID = re.compile(r"^-\s+\[(?P<done>[ x])\]\s+(?P<id>T\d{2})\s+(?P<title>.+)$", re.MULTILINE)


def tasks_done(plan_text: str) -> tuple[int, int, list[str]]:
    done = 0
    total = 0
    current: list[str] = []
    for match in TASK_ID.finditer(plan_text):
        total += 1
        if match.group("done") == "x":
            done += 1
        else:
            current.append(f"{match.group('id')} {match.group('title')}")
    return done, total, current


def progress_lines(text: str) -> tuple[str | None, list[str]]:
    current = None
    checkpoint_start = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Current task:"):
            current = stripped[len("Current task:"):].strip()
        elif stripped.startswith("## In progress"):
            checkpoint_start = len(text.splitlines())
    checkpoints = []
    if checkpoint_start is not None:
        body = text.splitlines()[checkpoint_start + 1 :]
        for line in body:
            if line.startswith("##"):
                break
            if line.strip() and line.strip() != "(none)":
                checkpoints.append(line.strip())
    return current, checkpoints


def print_section(title: str) -> None:
    print()
    print(f"-- {title}")


def main(argv: list[str]) -> int:
    print(f"StratifyAI status ({ROOT.name})")

    if PLAN.is_file():
        done, total, open_tasks = tasks_done(PLAN.read_text(encoding="utf-8"))
        print_section(f"Tasks {done}/{total} done")
        for task in open_tasks[:3]:
            print(f"  next: {task}")
    else:
        print_section("Tasks")
        print("  docs/PLAN.md not found")

    if PROGRESS.is_file():
        current, checkpoints = progress_lines(PROGRESS.read_text(encoding="utf-8"))
        print_section("Progress")
        print(f"  current task: {current or '(none)'}")
        for line in checkpoints:
            print(f"  in progress: {line}")
    else:
        print_section("Progress")
        print("  docs/PROGRESS.md not found")

    print_section("Last commits")
    if (ROOT / ".git").is_dir():
        log = subprocess.run(["git", "log", "-3", "--oneline"],
                             check=False, capture_output=True, text=True, cwd=ROOT)
        for line in log.stdout.strip().splitlines():
            print(f"  {line}")
        if not log.stdout.strip():
            print("  (no commits yet)")
    else:
        print("  (not a git repository)")

    if "--no-tests" in argv:
        print_section("Tests")
        print("  skipped (--no-tests)")
        return 0

    print_section("Tests (quick)")
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                                check=False, cwd=ROOT, text=True)
        tail = [line for line in result.stdout.strip().splitlines() if line.strip()][-1:]
        print(f"  {' '.join(tail).strip() if tail else 'no output'}")
        print(f"  exit code {result.returncode}")
        return 0
    except FileNotFoundError:
        print("  pytest is not installed; run `python run.py setup`")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
