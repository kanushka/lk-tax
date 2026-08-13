#!/usr/bin/env python3
"""Archive current official IRD individual income-tax forms by assessment year."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_PAGE = "https://www.ird.gov.lk/en/Downloads/SitePages/Forms.aspx?menuid=1603"
USER_AGENT = "lk-tax-archive/1.0 (personal research archive)"

# This small, intentionally curated set is the individual filing pack currently
# published on the official forms page. Do not silently substitute one tax year
# for another; add a new assessment-year entry only after IRD publishes it.
FORM_CATALOG: dict[str, list[dict[str, str]]] = {
    "2025-2026": [
        {
            "id": "return_of_income",
            "title": "Return of Income (Asmt_IIT_001_E)",
            "url": "https://www.ird.gov.lk/en/Downloads/IT_Individuals_Doc/Asmt_IIT_001_2025_2026_E.pdf",
            "local_path": "return-pack/Asmt_IIT_001_2025_2026_E.pdf",
        },
        {
            "id": "return_schedules",
            "title": "Schedules to Return of Income (Asmt_IIT_002_E)",
            "url": "https://www.ird.gov.lk/en/Downloads/IT_Individuals_Doc/Asmt_IIT_002_2025_2026_E.pdf",
            "local_path": "return-pack/Asmt_IIT_002_2025_2026_E.pdf",
        },
        {
            "id": "assets_and_liabilities",
            "title": "Statement of Assets and Liabilities (Asmt_IIT_003_E)",
            "url": "https://www.ird.gov.lk/en/Downloads/IT_Individuals_Doc/Asmt_IIT_003_2025_2026_E.pdf",
            "local_path": "return-pack/Asmt_IIT_003_2025_2026_E.pdf",
        },
        {
            "id": "return_completion_guide",
            "title": "Guide to filling the Return and Schedules (Asmt_IIT_004_E)",
            "url": "https://www.ird.gov.lk/en/Downloads/IT_Individuals_Doc/Asmt_IIT_004_2025_2026_E.pdf",
            "local_path": "return-pack/Asmt_IIT_004_2025_2026_E.pdf",
        },
        {
            "id": "estimated_tax_statement",
            "title": "Statement of Estimated Income Tax Payable (SET_E)",
            "url": "https://www.ird.gov.lk/en/Downloads/IT_SET_Doc/SET_2025_2026_E.pdf",
            "local_path": "estimated-tax/SET_2025_2026_E.pdf",
        },
        {
            "id": "estimated_tax_credit_schedule",
            "title": "Statement of Estimated Tax - Credit Schedule",
            "url": "https://www.ird.gov.lk/en/Downloads/IT_SET_Doc/SET_Schedule_25_26(Tax_Credit)_E.pdf",
            "local_path": "estimated-tax/SET_Schedule_25_26(Tax_Credit)_E.pdf",
        },
        {
            "id": "estimated_tax_guide",
            "title": "Guide to estimated tax and quarterly instalments (SET-E 2025/2026)",
            "url": "https://www.ird.gov.lk/en/Downloads/IT_SET_Doc/SET_25_26_Detail_Guide_E.pdf",
            "local_path": "estimated-tax/SET_25_26_Detail_Guide_E.pdf",
        },
        {
            "id": "apit_t10_certificate_amended",
            "title": "APIT/T.10 Certificate of Income Tax Deductions (2025/2026, amended)",
            "url": "https://www.ird.gov.lk/en/Downloads/Forms_APIT_Doc/APIT_T10_2526_AMD_EST.pdf",
            "local_path": "employment-credit/APIT_T10_2526_AMD_EST.pdf",
        },
    ]
}

ASSESSMENT_YEAR_STATUS = {
    "2025-2026": "published",
    "2026-2027": "not_published_on_source_page",
}


def documents_for_assessment_year(assessment_year: str) -> list[dict[str, str]]:
    """Return the explicitly published individual filing documents for a year."""
    return list(FORM_CATALOG.get(assessment_year, []))


def assessment_year_status(assessment_year: str) -> str:
    """Return whether the official forms page currently publishes the year pack."""
    return ASSESSMENT_YEAR_STATUS.get(assessment_year, "not_checked")


def fetch_pdf(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        data = response.read()
        content_type = response.headers.get_content_type()
    if not data.startswith(b"%PDF"):
        raise ValueError(f"expected a PDF, received {content_type}")
    return data


def write_pending_note(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "README.md").write_text(
        "# Assessment year 2026/2027\n\n"
        "As at the forms-page check recorded in `../manifest.json`, the official IRD "
        "Forms and Returns page did not list an individual Return of Income pack or "
        "a Statement of Estimated Income Tax Payable for this assessment year. "
        "This directory intentionally contains no substituted 2025/2026 form.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/ird/forms/individual"))
    parser.add_argument("--no-download", action="store_true", help="create only a manifest and status notes")
    args = parser.parse_args()

    retrieved_at = datetime.now(timezone.utc).isoformat()
    entries: list[dict[str, object]] = []
    for assessment_year, status in ASSESSMENT_YEAR_STATUS.items():
        year_directory = args.output / assessment_year
        if status != "published":
            write_pending_note(year_directory)
            entries.append({"assessment_year": assessment_year, "status": status, "documents": []})
            continue

        documents: list[dict[str, object]] = []
        for document in documents_for_assessment_year(assessment_year):
            record: dict[str, object] = dict(document)
            destination = year_directory / document["local_path"]
            if args.no_download:
                record["status"] = "not_downloaded"
            else:
                try:
                    data = fetch_pdf(document["url"])
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(data)
                    record.update(
                        status="downloaded",
                        bytes=len(data),
                        sha256=hashlib.sha256(data).hexdigest(),
                    )
                except Exception as error:
                    record.update(status="failed", error=str(error))
            documents.append(record)
        entries.append({"assessment_year": assessment_year, "status": status, "documents": documents})

    manifest = {
        "collection": "Sri Lanka IRD individual income-tax forms",
        "source_page": SOURCE_PAGE,
        "source_page_checked_at_utc": retrieved_at,
        "entries": entries,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    downloaded = sum(
        document.get("status") == "downloaded"
        for entry in entries
        for document in entry["documents"]
    )
    failed = sum(
        document.get("status") == "failed"
        for entry in entries
        for document in entry["documents"]
    )
    print(f"Downloaded {downloaded} official individual form documents; failed {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
