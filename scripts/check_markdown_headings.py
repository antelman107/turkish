#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


HEADING_RE = re.compile(r"^(#{1,2})\s+")
FENCE_RE = re.compile(r"^(```|~~~)")


@dataclass(frozen=True)
class Violation:
    path: Path
    line_no: int
    line: str


def iter_markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".md"):
                files.append(Path(dirpath) / name)
    return sorted(files)


def find_violations(file_path: Path) -> list[Violation]:
    violations: list[Violation] = []
    in_fence = False

    with file_path.open("r", encoding="utf-8") as f:
        for idx, raw in enumerate(f, start=1):
            line = raw.rstrip("\n")

            # Ignore markdown headings inside fenced code blocks.
            if FENCE_RE.match(line.strip()):
                in_fence = not in_fence
                continue

            if in_fence:
                continue

            if HEADING_RE.match(line):
                violations.append(Violation(file_path, idx, line))

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that articles don't use headings above level 3 (no # or ##)."
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1] / "content"),
        help="Path to Hugo content directory (default: golangforall/content).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"ERROR: root does not exist: {root}", file=sys.stderr)
        return 2

    all_violations: list[Violation] = []
    for md in iter_markdown_files(root):
        all_violations.extend(find_violations(md))

    if not all_violations:
        return 0

    print("Found headings above level 3 (disallowed # / ##):", file=sys.stderr)
    for v in all_violations:
        rel = v.path.relative_to(root)
        print(f"- {rel}:{v.line_no}: {v.line}", file=sys.stderr)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())


