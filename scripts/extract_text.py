#!/usr/bin/env python3
"""Write a searchable text sidecar (`<name>.pdf.md`) beside every corpus PDF.

Pages with a text layer use `pdftotext`; scanned pages fall back to OCR with
`pdftoppm` and `tesseract`. A sidecar is rewritten only when the manifest
checksum differs from the one recorded in its front matter.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from corpus import Document, iter_documents, sidecar_path  # noqa: E402

MIN_TEXT_CHARS = 100
MIN_WORD_TOKENS = 30
MIN_COMMON_WORD_RATIO = 0.05
COMMON_WORDS = frozenset(
    "the of and to in for is on by be or as a this that with shall tax income".split()
)
DISCLAIMER = "> Machine-extracted text for search. Confirm every figure against the PDF before relying on it."


class ExtractionError(Exception):
    pass


def needs_ocr(text: str) -> bool:
    if len("".join(text.split())) < MIN_TEXT_CHARS:
        return True
    words = [token.lower() for token in text.split() if token.isalpha()]
    if len(words) < MIN_WORD_TOKENS:
        return False
    common = sum(1 for word in words if word in COMMON_WORDS)
    return common / len(words) < MIN_COMMON_WORD_RATIO


def _run(run, cmd: list[str]) -> str:
    try:
        result = run(cmd, capture_output=True, encoding="utf-8", errors="replace", check=False)
    except OSError as exc:
        raise ExtractionError(f"{cmd[0]}: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        raise ExtractionError(f"{cmd[0]} exited {result.returncode}" + (f": {detail[-1]}" if detail else ""))
    return result.stdout


def extract_pages(pdf_path: Path, run=subprocess.run) -> list[tuple[str, str]]:
    info = _run(run, ["pdfinfo", str(pdf_path)])
    match = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
    if not match:
        raise ExtractionError("pdfinfo: no page count")
    page_count = int(match.group(1))
    if page_count < 1:
        raise ExtractionError("pdfinfo: page count below 1")
    pages: list[tuple[str, str]] = []
    for number in range(1, page_count + 1):
        page = str(number)
        text = _run(run, ["pdftotext", "-layout", "-f", page, "-l", page, str(pdf_path), "-"])
        if not needs_ocr(text):
            pages.append(("text", text))
            continue
        with tempfile.TemporaryDirectory() as tmp:
            stem = str(Path(tmp) / "page")
            _run(run, ["pdftoppm", "-r", "300", "-f", page, "-l", page, "-png", "-singlefile", str(pdf_path), stem])
            pages.append(("ocr", _run(run, ["tesseract", f"{stem}.png", "-", "-l", "eng"])))
    return pages


def render_sidecar(doc: Document, pages: list[tuple[str, str]]) -> str:
    ocr_pages = [str(i) for i, (method, _) in enumerate(pages, 1) if method == "ocr"]
    parts = [
        "---\n"
        f"source: {doc.local_path}\n"
        f"source_url: {doc.source_url}\n"
        f"source_sha256: {doc.sha256}\n"
        f"pages: {len(pages)}\n"
        f"ocr_pages: [{', '.join(ocr_pages)}]\n"
        "---\n\n"
        f"{DISCLAIMER}\n"
    ]
    for number, (_, text) in enumerate(pages, 1):
        parts.append(f"\n## Page {number}\n\n{text.strip()}\n")
    return "".join(parts)


def sidecar_sha(path: Path) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, ValueError):
        return None
    if not lines or lines[0] != "---":
        return None
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("source_sha256:"):
            return line.split(":", 1)[1].strip()
    return None


def write_atomic(path: Path, content: str) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None, run=subprocess.run) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", type=Path, default=Path("data/ird"))
    parser.add_argument("--check", action="store_true", help="report missing or stale sidecars without extracting")
    args = parser.parse_args(argv)

    failures = 0
    for doc in iter_documents(args.data_root):
        if not doc.pdf_path.exists():
            print(f"MISSING {doc.pdf_path}")
            failures += 1
            continue
        sidecar = sidecar_path(doc.pdf_path)
        current = sidecar_sha(sidecar) == doc.sha256
        if args.check:
            if not current:
                state = "stale" if sidecar.exists() else "missing"
                print(f"{state} {sidecar}")
                failures += 1
            continue
        if current:
            print(f"current {sidecar}")
            continue
        try:
            pages = extract_pages(doc.pdf_path, run=run)
        except ExtractionError as exc:
            print(f"FAILED {doc.pdf_path}: {exc}")
            failures += 1
            continue
        try:
            write_atomic(sidecar, render_sidecar(doc, pages))
        except OSError as exc:
            print(f"FAILED {sidecar}: {exc}")
            failures += 1
            continue
        print(f"extracted {sidecar}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
