#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


HEADING_RE = re.compile(r"^(#{1,6})\s+")
FENCE_RE = re.compile(r"^(```|~~~)")


@dataclass(frozen=True)
class Change:
    path: Path
    line_no: int
    before: str
    after: str


def iter_markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".md"):
                files.append(Path(dirpath) / name)
    return sorted(files)


def capitalize_first_cased_char(s: str) -> str:
    # We want "all headings start with a capital letter", but headings may start
    # with punctuation/quotes. So we uppercase the first cased (alphabetic) char.
    chars = list(s)
    for i, ch in enumerate(chars):
        # "Cased" chars have different lower/upper forms.
        if ch.isalpha() and ch.lower() != ch.upper():
            chars[i] = ch.upper()
            break
    return "".join(chars)


def process_text(text: str) -> tuple[str, list[tuple[int, str, str]]]:
    lines = text.splitlines(keepends=True)
    in_fence = False
    edits: list[tuple[int, str, str]] = []

    for idx, raw in enumerate(lines, start=1):
        line_no_nl = raw.rstrip("\n")
        stripped = line_no_nl.strip()

        if FENCE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        m = HEADING_RE.match(line_no_nl)
        if not m:
            continue

        prefix_end = m.end()
        prefix = line_no_nl[:prefix_end]
        rest = line_no_nl[prefix_end:]
        updated_rest = capitalize_first_cased_char(rest)
        if updated_rest != rest:
            before = line_no_nl
            after = prefix + updated_rest
            # Preserve original newline (if any)
            nl = "\n" if raw.endswith("\n") else ""
            lines[idx - 1] = after + nl
            edits.append((idx, before, after))

    return "".join(lines), edits


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capitalize the first letter of every markdown heading (outside fenced code blocks)."
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1] / "content"),
        help="Path to Hugo content directory (default: golangforall/content).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Don't modify files; exit 1 if any file would change.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"ERROR: root does not exist: {root}", file=sys.stderr)
        return 2

    total = 0
    changed_files = 0
    all_changes: list[Change] = []

    for md in iter_markdown_files(root):
        total += 1
        original = md.read_text(encoding="utf-8")
        updated, edits = process_text(original)
        if updated == original:
            continue

        changed_files += 1
        for line_no, before, after in edits:
            all_changes.append(Change(md, line_no, before, after))

        if not args.check:
            md.write_text(updated, encoding="utf-8")

    print(f"Processed: {total} markdown files")
    print(f"Changed:   {changed_files} files (headings capitalized)")

    if args.check and changed_files:
        # Print a short sample to help locate issues.
        sample = all_changes[:20]
        print("\nSample changes (first 20):", file=sys.stderr)
        for ch in sample:
            rel = ch.path.relative_to(root)
            print(f"- {rel}:{ch.line_no}: {ch.before}  ->  {ch.after}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


