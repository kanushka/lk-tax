#!/usr/bin/env python3
"""Sync circular metadata stubs and regenerate the corpus INDEX.md."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))

from corpus import sidecar_path  # noqa: E402

TAX_TYPES = ("income_tax", "apit", "wht_ait", "vat", "svat", "sscl", "other")
TOPICS = (
    "instalments",
    "employment",
    "withholding",
    "returns_filing",
    "tin_registration",
    "reliefs_exemptions",
    "interest_dividends",
    "foreign_income",
    "penalties_interest",
    "administration",
    "indirect_tax",
    "other",
)

STUB = {
    "circular_no": None,
    "revision": None,
    "date": None,
    "subject": None,
    "summary": None,
    "tax_types": [],
    "topics": [],
    "assessment_years": None,
    "revises": [],
    "revised_by": [],
    "relevant_to_individuals": None,
    "reviewed": False,
}
PARSED_FIELDS = ("circular_no", "revision", "date")

MONTHS = {m: i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), start=1)}

NUMBER_AFTER_LABEL = re.compile(r"Circular\s+No[:.]?\s*:?\s*([A-Za-z0-9][A-Za-z0-9/\-]*)", re.IGNORECASE)
NUMBER_BARE = re.compile(r"\b(?:SEC|CGIR)\b[\s./]*(\d{4}(?:/[A-Za-z0-9\-]+)+)", re.IGNORECASE)
REVISION = re.compile(r"\(\s*(Re-Revised|Revised)\s*\)", re.IGNORECASE)
BRACKET = re.compile(r"\[([^\[\]]*)\]")
DATE_WORDS = re.compile(r"(\d{1,2})[\s.]*([A-Za-z]{3,})[\s.]*(\d{4})")
DATE_NUMERIC = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")


def _parse_date(text: str) -> str | None:
    numeric = DATE_NUMERIC.search(text)
    if numeric:
        day, month, year = (int(g) for g in numeric.groups())
        return f"{year:04d}-{month:02d}-{day:02d}"
    words = DATE_WORDS.search(text)
    if words and words.group(2)[:3].lower() in MONTHS:
        month = MONTHS[words.group(2)[:3].lower()]
        return f"{int(words.group(3)):04d}-{month:02d}-{int(words.group(1)):02d}"
    return None


def parse_title(title: str) -> dict:
    number = None
    labelled = NUMBER_AFTER_LABEL.search(title)
    if labelled:
        number = labelled.group(1).upper()
    else:
        bare = NUMBER_BARE.search(title)
        if bare:
            number = "SEC/" + bare.group(1).upper()
    revision_match = REVISION.search(title)
    brackets = BRACKET.findall(title)
    return {
        "circular_no": number,
        "revision": revision_match.group(1).title() if revision_match else None,
        "date": _parse_date(brackets[-1]) if brackets else None,
    }


def sync_metadata(manifest: dict, metadata: dict) -> dict:
    result: dict = {}
    paths = {e["local_path"] for e in manifest.get("entries", [])}
    for entry in manifest.get("entries", []):
        path = entry["local_path"]
        if path in metadata:
            current = dict(metadata[path])
        else:
            current = copy.deepcopy(STUB)
        parsed = parse_title(entry.get("title", ""))
        for field in PARSED_FIELDS:
            if current.get(field) is None:
                current[field] = parsed[field]
        result[path] = current
    for path, value in metadata.items():
        if path not in paths:
            result[path] = value
    return result


def validate_metadata(metadata: dict, manifest: dict) -> list[str]:
    known = {e["local_path"] for e in manifest.get("entries", [])}
    errors = []
    for path, item in metadata.items():
        for value in item.get("tax_types", []):
            if value not in TAX_TYPES:
                errors.append(f"{path}: unknown tax_type {value!r}")
        for value in item.get("topics", []):
            if value not in TOPICS:
                errors.append(f"{path}: unknown topic {value!r}")
        for field in ("revises", "revised_by"):
            for value in item.get(field, []):
                if value not in known:
                    errors.append(f"{path}: {field} {value!r} is not a manifest local_path")
    return errors


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def _link(label: str, relative: str) -> str:
    return f"[{label}]({quote(relative, safe='/:%?=&~')})"


def _doc_links(relative: str, source_url: str) -> tuple[str, str, str]:
    text = sidecar_path(Path(relative)).as_posix()
    return _link("text", text), _link("pdf", relative), _link("source", source_url)


def _status(item: dict, by_path: dict) -> str:
    if not item.get("reviewed"):
        return "metadata pending"
    revised_by = item.get("revised_by") or []
    if revised_by:
        later = by_path.get(revised_by[0], {})
        return f"revised by {later.get('circular_no') or revised_by[0]} ({later.get('revision') or 'original'})"
    return "latest in corpus"


def render_index(circulars: dict, metadata: dict, forms: dict) -> str:
    entries = circulars.get("entries", [])
    manifest_paths = {e["local_path"] for e in entries}
    lines = [
        "# IRD corpus index",
        "",
        "Generated by `scripts/build_index.py`; do not edit. Curated fields live in "
        "`data/ird/circulars/metadata.json`. To find the documents that apply to an assessment year, "
        "use the lookup skill: read this index, pick rows by Years and Topics, then open the Text "
        "sidecar and confirm figures against the PDF.",
        "",
        "Topics: " + ", ".join(f"`{t}`" for t in TOPICS),
        "",
        "Tax types: " + ", ".join(f"`{t}`" for t in TAX_TYPES),
        "",
        "## Circulars",
        "",
        "| Circular | Date | Subject | Years | Topics | Status | Text | PDF | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        path = entry["local_path"]
        item = metadata.get(path, {})
        relative = f"circulars/{path}"
        text, pdf, source = _doc_links(relative, entry["source_url"])
        number = item.get("circular_no") or ""
        if item.get("revision"):
            number = f"{number} ({item['revision']})"
        years = item.get("assessment_years")
        row = [
            number,
            item.get("date") or "",
            item.get("subject") or entry.get("title", ""),
            ", ".join(years) if years else "",
            ", ".join(item.get("topics", [])),
            _status(item, metadata),
        ]
        lines.append("| " + " | ".join([*(_cell(c) for c in row), text, pdf, source]) + " |")
    lines += [
        "",
        "## Individual forms",
        "",
        "| Year | Document | Text | PDF | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for year_entry in forms.get("entries", []):
        year = year_entry["assessment_year"]
        documents = year_entry.get("documents", [])
        if not documents:
            lines.append(f"| {_cell(year)} | not published on source page |  |  |  |")
            continue
        for doc in documents:
            relative = f"forms/individual/{year}/{doc['local_path']}"
            text, pdf, source = _doc_links(relative, doc["url"])
            lines.append(f"| {_cell(year)} | {_cell(doc.get('title', ''))} | {text} | {pdf} | {source} |")
    orphans = [p for p in metadata if p not in manifest_paths]
    if orphans:
        lines += ["", "## Orphaned metadata", "", "Metadata entries with no matching manifest document:", ""]
        lines += [f"- `{p}`" for p in orphans]
    return "\n".join(lines) + "\n"


def _load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _dump(metadata: dict) -> str:
    return json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", type=Path, default=Path("data/ird"))
    parser.add_argument("--check", action="store_true", help="fail if metadata.json or INDEX.md would change")
    args = parser.parse_args(argv)

    root: Path = args.data_root
    circulars = _load(root / "circulars" / "manifest.json", {"entries": []})
    forms = _load(root / "forms" / "individual" / "manifest.json", {"entries": []})
    metadata_path = root / "circulars" / "metadata.json"
    index_path = root / "INDEX.md"

    metadata = sync_metadata(circulars, _load(metadata_path, {}))
    errors = validate_metadata(metadata, circulars)
    for error in errors:
        print(f"INVALID {error}")
    metadata_text = _dump(metadata)
    index_text = render_index(circulars, metadata, forms)

    outputs = ((metadata_path, metadata_text), (index_path, index_text))
    if args.check:
        stale = 0
        for path, text in outputs:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                print(f"stale {path}")
                stale += 1
        return 1 if errors or stale else 0

    for path, text in outputs:
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
