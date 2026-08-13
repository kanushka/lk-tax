#!/usr/bin/env python3
"""Download the IRD Circulars listing into a reproducible local archive.

The script reads the official listing, writes PDFs to `data/ird/circulars/<year>/`,
and records every source entry in `manifest.json`. Re-run it to add or refresh
documents without manually maintaining a list of URLs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


DEFAULT_LISTING_URL = (
    "https://www.ird.gov.lk/en/publications/sitepages/Circulars.aspx?menuid=1506"
)
USER_AGENT = "lk-tax-archive/1.0 (personal research archive)"


def request_url(url: str) -> str:
    """Encode URL paths safely while retaining query strings and fragments."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path), parts.query, parts.fragment))


class CircularLinkParser(HTMLParser):
    """Extract the document links and human-readable labels from the IRD list."""

    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.entries: list[dict[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href and "/Circulars_Circulars/" in href:
            self._href = urljoin(self.page_url, href)
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            title = re.sub(r"\s+", " ", unescape("".join(self._parts))).strip()
            self.entries.append({"title": title, "url": self._href})
            self._href = None
            self._parts = []


def source_filename(url: str) -> str:
    name = Path(unescape(urlsplit(url).path)).name
    return re.sub(r"[^A-Za-z0-9._() -]+", "_", name).strip(" .") or "circular.pdf"


def infer_year(entry: dict[str, str]) -> str:
    for value in (entry["title"], entry["url"]):
        match = re.search(r"(?:SEC|CGIR)[/_-]?(20\d{2})", value, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"\b(20\d{2})\b", value)
        if match:
            return match.group(1)
    return "undated"


def unique_path(directory: Path, filename: str, reserved: set[Path]) -> Path:
    candidate = directory / filename
    if candidate not in reserved:
        reserved.add(candidate)
        return candidate
    stem, suffix = Path(filename).stem, Path(filename).suffix
    number = 2
    while True:
        candidate = directory / f"{stem}_{number}{suffix}"
        if candidate not in reserved:
            reserved.add(candidate)
            return candidate
        number += 1


def download(url: str, destination: Path) -> tuple[int, str]:
    request = Request(request_url(url), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        data = response.read()
        content_type = response.headers.get_content_type()
    if not data.startswith(b"%PDF"):
        raise ValueError(f"expected a PDF, received {content_type}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return len(data), hashlib.sha256(data).hexdigest()


def verify_archive(output: Path) -> int:
    """Check every downloaded file against the checksum recorded in the manifest."""
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    checked = 0
    for entry in manifest["entries"]:
        if entry.get("status") != "downloaded":
            failures.append(f"not downloaded: {entry['local_path']}")
            continue
        file_path = output / entry["local_path"]
        if not file_path.is_file():
            failures.append(f"missing: {entry['local_path']}")
            continue
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if digest != entry.get("sha256"):
            failures.append(f"checksum mismatch: {entry['local_path']}")
            continue
        checked += 1
    if failures:
        print("Archive verification failed:\n" + "\n".join(failures), file=sys.stderr)
        return 1
    print(f"Verified {checked} downloaded circulars against manifest checksums.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listing-url", default=DEFAULT_LISTING_URL)
    parser.add_argument("--output", type=Path, default=Path("data/ird/circulars"))
    parser.add_argument("--no-download", action="store_true", help="write the manifest without PDFs")
    parser.add_argument("--verify", action="store_true", help="verify local files against manifest checksums")
    args = parser.parse_args()

    if args.verify:
        return verify_archive(args.output)

    listing_request = Request(request_url(args.listing_url), headers={"User-Agent": USER_AGENT})
    with urlopen(listing_request, timeout=60) as response:
        listing_html = response.read().decode("utf-8", errors="replace")

    parser_html = CircularLinkParser(args.listing_url)
    parser_html.feed(listing_html)
    entries = parser_html.entries
    if not entries:
        raise RuntimeError("no IRD circular document links were found on the listing page")

    args.output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    reserved: set[Path] = set()
    retrieved_at = datetime.now(timezone.utc).isoformat()

    for position, entry in enumerate(entries, start=1):
        year = infer_year(entry)
        relative_path = unique_path(Path(year), source_filename(entry["url"]), reserved)
        destination = args.output / relative_path
        record: dict[str, object] = {
            "position": position,
            "title": entry["title"],
            "source_url": entry["url"],
            "year": year,
            "local_path": relative_path.as_posix(),
            "retrieved_at_utc": retrieved_at,
        }
        if args.no_download:
            record["status"] = "not_downloaded"
        else:
            try:
                byte_count, checksum = download(entry["url"], destination)
                record.update(status="downloaded", bytes=byte_count, sha256=checksum)
            except Exception as error:  # Keep failures visible for a retry rather than hiding them.
                record.update(status="failed", error=str(error))
                print(f"FAILED: {entry['url']}: {error}", file=sys.stderr)
        records.append(record)

    manifest = {
        "collection": "Sri Lanka Inland Revenue Department circulars",
        "listing_url": args.listing_url,
        "retrieved_at_utc": retrieved_at,
        "entry_count": len(records),
        "downloaded_count": sum(record["status"] == "downloaded" for record in records),
        "failed_count": sum(record["status"] == "failed" for record in records),
        "entries": records,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Found {len(records)} circulars; downloaded {manifest['downloaded_count']}; "
        f"failed {manifest['failed_count']}."
    )
    return 0 if manifest["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
