#!/usr/bin/env python3
"""Split PROMPT_PACK.md into the real project files.

A block starts on its own line of the form:

    %%%FILE <relative/path>%%%

(and `% % %FILE <path> %%% ` with the space before the closing marker also
works), and finishes on a line containing only ``%%%END%%%``. Text outside the
blocks (the pack header, the "## File:" headings, "---" separators) is ignored.

The markers are matched line-anchored with ``re.MULTILINE``, so a mention of
``%%%FILE ... %%%`` or ``%%%END%%%`` inside a sentence does not open or close a
block.

Usage:
    python scripts/split_pack.py [PACK] [--force]

``--force`` allows overwriting files that already exist; without it the script
refuses rather than clobbering.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Line-anchored, so only a marker sitting alone on a line counts. `.` does not
# match a newline (DOTALL is not set), so a path can never span lines.
BLOCK_START = re.compile(r"^%%%FILE[ \t]+(?P<path>[^\n]+?)[ \t]*%%%\n", re.MULTILINE)
BLOCK_END = re.compile(r"^%%%END%%%\n", re.MULTILINE)

ROOT_MARKER = "%%%"


def extract_blocks(text: str) -> list[tuple[str, str]]:
    """Return (relative_path, content) pairs found in *text*."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks: list[tuple[str, str]] = []
    for start in BLOCK_START.finditer(text):
        rel_path = start.group("path").strip()
        end = BLOCK_END.search(text, start.end())
        if end is None:
            raise SystemExit(f"error: block for '{rel_path}' has no {ROOT_MARKER}END{ROOT_MARKER} line")
        content = text[start.end() : end.start()]
        blocks.append((rel_path, content))
    return blocks


def _inside_root(dest: Path, root: Path) -> bool:
    """True if *dest* is *root* itself or lives somewhere under it."""
    return dest == root or root in dest.parents


def split_pack(pack_path: Path, root: Path, force: bool) -> list[str]:
    """Write every block of *pack_path* under *root*; return the paths written."""
    text = pack_path.read_text(encoding="utf-8")
    blocks = extract_blocks(text)
    if not blocks:
        raise SystemExit(f"error: no {ROOT_MARKER}FILE ... {ROOT_MARKER} blocks found in {pack_path}")

    written: list[str] = []
    for rel_path, content in blocks:
        dest = (root / rel_path).resolve()
        if not _inside_root(dest, root):
            raise SystemExit(f"error: refusing to write outside the project root: {rel_path}")
        if dest.exists() and not force:
            raise SystemExit(f"error: refusing to overwrite existing file: {rel_path} (use --force)")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        written.append(rel_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Split a PROMPT_PACK.md into its file blocks.")
    parser.add_argument("pack", nargs="?", default="PROMPT_PACK.md", help="path to the pack (default: PROMPT_PACK.md)")
    parser.add_argument("--force", action="store_true", help="overwrite files that already exist")
    args = parser.parse_args(argv)

    root = Path.cwd().resolve()
    pack_path = (root / args.pack).resolve()
    if not _inside_root(pack_path, root):
        raise SystemExit(f"error: pack path is outside the project root: {args.pack}")
    if not pack_path.is_file():
        raise SystemExit(f"error: pack not found: {args.pack}")

    written = split_pack(pack_path, root, force=args.force)
    print(f"Extracted {len(written)} file(s):")
    for rel_path in written:
        print(f"  {rel_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
