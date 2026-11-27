# Corpus text sidecars, index, and lookup skill

## Why

Agents answering a tax question re-read (and re-OCR) PDFs every session. The
corpus is 77 PDFs / 515 pages; about 60% have no text layer. Convert once, index
once, and give agents a fixed lookup routine.

## Goals

- Every PDF in `data/ird/` has a searchable text sidecar, regenerated only when
  the PDF changes.
- One index file tells an agent which documents apply to an assessment year and
  which were revised or superseded.
- A skill makes the lookup routine repeatable and keeps the AGENTS.md evidence
  rules (year discipline, later-revision check, citations).

## Non-goals

- Structured rates/slabs data per year.
- Embeddings or vector search.
- Field-by-field maps of the forms (possible follow-up).
- Sinhala/Tamil OCR; only English body text matters, letterhead noise is accepted.

## Anti-goal

An answer that quotes a figure from OCR text without checking the PDF. Sidecars
are for finding, PDFs remain the evidence.

## Approaches considered

- A. Text sidecars only: cheap, but the agent still cannot tell which circular
  applies to a year or what replaced what.
- **B. Sidecars + index + skill: chosen.** Adds the missing routing layer and
  stays greppable and auditable.
- C. Structured rules JSON: fastest for calculations, but hand-curated
  interpretation; a wrong entry is a silently wrong answer.

## Design

### 1. Text sidecars — `scripts/extract_text.py`

- Output beside the source: `X.pdf` → `X.pdf.md`.
- Per page: `pdftotext -layout`; if the page yields under ~100 non-space
  characters, render at 300 dpi (`pdftoppm`) and OCR with `tesseract -l eng`.
- Sidecar layout: front matter (`source_sha256`, `pages`, per-page method
  `text`/`ocr`, tool versions), then one `## Page N` section per page so
  citations can name a page.
- Incremental: skip when the sidecar's `source_sha256` equals the manifest
  value. Existing sidecars are never regenerated for an unchanged PDF, so
  tesseract version differences between machines cause no churn.
- `--check` exits non-zero if any downloaded manifest entry lacks a current
  sidecar.
- Covers circulars and forms (reads both manifests).
- One-time cost measured at ~5 s per OCR page, roughly 30–40 minutes total.

### 2. Metadata — `data/ird/circulars/metadata.json`

Curated file, separate from `manifest.json` so the download script never
overwrites it. Keyed by `local_path`:

- `circular_no`, `date` (parsed from the manifest title where possible)
- `subject`, `summary` (one or two lines)
- `tax_types`, `topics`
- `assessment_years` (list or from/to; `null` when the source does not say)
- `revises`, `revised_by` (only when the source states the relationship)
- `relevant_to_individuals`
- `reviewed` (false until a human or agent has checked the entry against the PDF)

Initial fill for the 69 circulars is done by an agent reading the sidecars, in
session. CI does not call an LLM: a new document gets a stub entry with
`reviewed: false`, and the index shows it as pending.

### 3. Index — `scripts/build_index.py` → `data/ird/INDEX.md`

Generated from the two manifests plus `metadata.json`. Newest first. Columns:
circular no, date, subject, assessment years, topics, status
(operative / revised by X / metadata pending), sidecar path, PDF path, source
URL. Forms listed in a second table by assessment year, including the
2026-2027 pending marker.

### 4. Skill — `.claude/skills/ird-lookup/SKILL.md`

Trigger: any Sri Lanka tax question, estimate, or filing draft in this repo.

1. Fix the assessment year (ask if missing).
2. Read `data/ird/INDEX.md`; shortlist by year and topic; follow `revised_by`
   to the latest version.
3. Grep and read the shortlisted sidecars. Treat `metadata pending` documents
   as unknown relevance and read them.
4. For every rate, threshold, date, or formula used in the answer, open that
   page of the PDF and confirm it.
5. Cite the PDF path, page, and manifest source URL, not the sidecar.

AGENTS.md gets a short pointer to the index and these steps so agents that do
not load Claude skills follow the same routine.

### 5. CI — `refresh-ird.yml`

- Install `poppler-utils` and `tesseract-ocr`.
- After download: run `extract_text.py`, then `build_index.py`.
- Existing change detection and `git add data` already cover the new files.

### 6. Tests

- Skip-by-checksum and regenerate-on-change.
- Text-vs-OCR page decision (extraction tools stubbed).
- Index build from a fixture manifest and metadata, including pending and
  revised rows.

## Left to the builder

- Exact front-matter keys and index column order.
- Character threshold for the OCR fallback.
- Topic vocabulary, kept small and listed at the top of `INDEX.md`.
