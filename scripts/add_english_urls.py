#!/usr/bin/env python3
# Adds ASCII (English) URLs to Hugo content markdown files.
# - Works with TOML front matter delimited by +++
# - If a file has no front matter, it creates one with only `url = ...`
# - If `url` already exists, file is left unchanged
#
# Usage:
#   python3 golangforall/scripts/add_english_urls.py
#
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


CONTENT_DIR = Path(__file__).resolve().parents[1] / "content"
URL_PREFIX = "/ru"


TURKISH_MAP = str.maketrans(
    {
        "ğ": "g",
        "Ğ": "g",
        "ş": "s",
        "Ş": "s",
        "ı": "i",
        "İ": "i",
        "ö": "o",
        "Ö": "o",
        "ü": "u",
        "Ü": "u",
        "ç": "c",
        "Ç": "c",
        "â": "a",
        "Â": "a",
        "î": "i",
        "Î": "i",
        "û": "u",
        "Û": "u",
    }
)


CYR_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def translit_to_ascii(s: str) -> str:
    s = s.translate(TURKISH_MAP)
    out: List[str] = []
    for ch in s:
        lower = ch.lower()
        if lower in CYR_MAP:
            out.append(CYR_MAP[lower])
        else:
            out.append(ch)
    return "".join(out)


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def slugify(s: str) -> str:
    s = translit_to_ascii(s).lower()
    s = s.replace("_", "-").replace(" ", "-")
    s = _NON_ALNUM_RE.sub("-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def strip_lang_suffix(stem: str) -> str:
    # Handles files like something.ru.md or something.en.md
    if stem.endswith(".ru"):
        return stem[: -len(".ru")]
    if stem.endswith(".en"):
        return stem[: -len(".en")]
    return stem


def compute_url(rel_path: Path) -> str:
    parts = list(rel_path.parts)
    filename = parts[-1]
    dirs = parts[:-1]

    # Treat Hugo section index files as directory URLs.
    # Supports both `_index.md` and `_index.<lang>.md` (e.g. `_index.ru.md`).
    stem = strip_lang_suffix(Path(filename).stem)
    if stem == "_index":
        segs = [slugify(d) for d in dirs]
        path = "/".join([URL_PREFIX] + segs) + "/"
        return path if path != f"{URL_PREFIX}/" else f"{URL_PREFIX}/"

    segs = [slugify(d) for d in dirs] + [slugify(stem)]
    return "/".join([URL_PREFIX] + segs) + "/"


def has_toml_front_matter(text: str) -> bool:
    return text.startswith("+++\n") or text.startswith("+++\r\n")


@dataclass
class FrontMatter:
    start: int
    end: int
    body: str


def extract_toml_front_matter(text: str) -> FrontMatter | None:
    if not has_toml_front_matter(text):
        return None
    # Find the second delimiter line "+++"
    # We require delimiters to be on their own line.
    m = re.search(r"(?m)^\+\+\+\s*$", text)
    if not m or m.start() != 0:
        return None
    m2 = re.search(r"(?m)^\+\+\+\s*$", text[m.end() :])
    if not m2:
        return None
    start = m.end()
    end = m.end() + m2.start()
    body = text[start:end]
    return FrontMatter(start=start, end=end, body=body)


def front_matter_has_url(body: str) -> bool:
    return re.search(r"(?m)^\s*url\s*=\s*['\"]", body) is not None


def insert_url_into_front_matter(text: str, url: str) -> str:
    fm = extract_toml_front_matter(text)
    if fm is None:
        # Create minimal TOML front matter.
        return f"+++\nurl = '{url}'\n+++\n\n{text}"

    if front_matter_has_url(fm.body):
        return text

    # Insert before closing delimiter (i.e., at fm.end)
    before = text[: fm.end]
    after = text[fm.end :]

    # Keep spacing: ensure there is a newline before url line unless already present
    if not before.endswith("\n"):
        before += "\n"
    before += f"url = '{url}'\n"
    return before + after


def iter_markdown_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.md"):
        if p.is_file():
            yield p


def main() -> int:
    if not CONTENT_DIR.exists():
        raise SystemExit(f"Content dir not found: {CONTENT_DIR}")

    urls_seen: Dict[str, Path] = {}
    collisions: List[Tuple[str, Path, Path]] = []

    changed = 0
    total = 0

    for md in sorted(iter_markdown_files(CONTENT_DIR)):
        total += 1
        rel = md.relative_to(CONTENT_DIR)
        url = compute_url(rel)

        if url in urls_seen:
            collisions.append((url, urls_seen[url], md))
        else:
            urls_seen[url] = md

        original = md.read_text(encoding="utf-8")
        updated = insert_url_into_front_matter(original, url)
        if updated != original:
            md.write_text(updated, encoding="utf-8")
            changed += 1

    print(f"Processed: {total} markdown files")
    print(f"Updated:   {changed} files (added missing url)")

    if collisions:
        print("\nURL collisions detected (please resolve):")
        for url, first, second in collisions:
            print(f"- {url}\n  - {first}\n  - {second}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


