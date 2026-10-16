#!/usr/bin/env python3
"""Scan project files for secret-like strings. Exit 1 if any match is found.

Scans the files Git would track: tracked files plus untracked files that are not
listed in .gitignore. Outside a repo it walks the tree instead. Binary and
oversize files are skipped. Matches are printed as file:line with the value
masked, so the scanner itself never leaks a secret.

Usage: python scripts/check_secrets.py [--quiet]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2_000_000

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", ".runtime", "docs/inputs",
}

# (label, pattern). Key material is required to be a long contiguous run so that
# ordinary hashes, UUIDs and long words do not trip the scan.
RULES: list[tuple[str, re.Pattern[bytes]]] = [
    ("private key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(rb"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(rb"(?i)gh[pousr]_[A-Za-z0-9_]{30,}")),
    ("Stripe key", re.compile(rb"(?i)sk_live_[0-9A-Za-z]{16,}")),
    ("Slack token", re.compile(rb"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("JWT", re.compile(rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("generic api key", re.compile(
        rb"(?i)\b(?:api[_-]?key|apikey|client_secret|access[_-]?key|secret)"
        rb"\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{24,}")),
    ("password assignment", re.compile(
        rb"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
]


def git_files() -> set[Path]:
    """Tracked plus untracked non-ignored files, empty if not a repository."""
    files: set[Path] = set()
    for args in (["ls-files", "-z"], ["ls-files", "--others", "--exclude-standard", "-z"]):
        try:
            result = subprocess.run(["git", *args], check=False, capture_output=True, text=True, cwd=ROOT)
        except (FileNotFoundError, OSError):
            return set()
        if result.returncode != 0:
            continue
        files.update(Path(part) for part in result.stdout.split("\0") if part)
    return files


def walk_files() -> set[Path]:
    files: set[Path] = set()
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        try:
            parts = path.relative_to(ROOT).parts
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in parts):
            continue
        files.add(path)
    return files


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def scan_file(path: Path) -> list[str]:
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if not data or len(data) > MAX_BYTES:
        return []
    if b"\0" in data[:4096]:
        return []
    findings: list[str] = []
    for number, line in enumerate(data.splitlines(), start=1):
        for label, pattern in RULES:
            if pattern.search(line):
                findings.append(f"  {relative(path)}:{number}: {label}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan project files for secret-like strings.")
    parser.add_argument("--quiet", action="store_true", help="print only matches, never the OK line")
    args = parser.parse_args(argv)

    files = git_files() or walk_files()
    findings: list[str] = []
    for path in sorted(files):
        findings.extend(scan_file(path))

    if findings:
        print(f"potential secrets found in {len(findings)} place(s):")
        print("\n".join(findings))
        return 1
    if not args.quiet:
        print(f"secret scan: no matches in {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
