"""Read the IRD corpus manifests as a flat list of downloaded documents."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Document:
    collection: str
    local_path: str
    pdf_path: Path
    sha256: str
    source_url: str
    title: str
    assessment_year: str | None = None


def sidecar_path(pdf_path: Path) -> Path:
    return pdf_path.with_name(pdf_path.name + ".md")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_documents(data_root: Path) -> Iterator[Document]:
    circulars_dir = data_root / "circulars"
    circulars_manifest = circulars_dir / "manifest.json"
    if circulars_manifest.exists():
        for entry in _load(circulars_manifest).get("entries", []):
            if entry.get("status") != "downloaded":
                continue
            yield Document(
                collection="circulars",
                local_path=entry["local_path"],
                pdf_path=circulars_dir / entry["local_path"],
                sha256=entry["sha256"],
                source_url=entry["source_url"],
                title=entry.get("title", ""),
            )

    forms_dir = data_root / "forms" / "individual"
    forms_manifest = forms_dir / "manifest.json"
    if forms_manifest.exists():
        for entry in _load(forms_manifest).get("entries", []):
            year = entry["assessment_year"]
            for item in entry.get("documents", []):
                if item.get("status") != "downloaded":
                    continue
                yield Document(
                    collection="forms",
                    local_path=item["local_path"],
                    pdf_path=forms_dir / year / item["local_path"],
                    sha256=item["sha256"],
                    source_url=item["url"],
                    title=item.get("title", ""),
                    assessment_year=year,
                )
