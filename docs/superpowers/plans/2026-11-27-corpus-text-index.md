# Corpus Text Sidecars, Index, and Lookup Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every PDF in `data/ird/` a searchable text sidecar, a generated index that routes by assessment year and revision status, and a skill that fixes the lookup routine.

**Architecture:** Two stdlib-only Python scripts sharing one small module that reads the existing manifests. `extract_text.py` writes `X.pdf.md` beside each PDF, shelling out to poppler and tesseract and skipping PDFs whose sha256 is unchanged. `build_index.py` keeps a curated `metadata.json` in sync with the circulars manifest and renders a deterministic `data/ird/INDEX.md`. A Claude skill plus an AGENTS.md pointer tell agents to use the index and sidecars to find, and the PDF to confirm.

**Tech Stack:** Python 3.12+ stdlib, `unittest`, `pdfinfo`/`pdftotext`/`pdftoppm` (poppler), `tesseract` (eng), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-27-corpus-text-index-design.md`

## Global Constraints

- No third-party Python packages; scripts follow the style of `scripts/download_ird_circulars.py` (argparse, `main() -> int`, `from __future__ import annotations`).
- External tools are invoked with argument lists, never through a shell.
- Tests use `unittest`, load scripts the way `tests/test_download_ird_individual_forms.py` does, and never call real poppler/tesseract. Run with `python3 -m unittest discover -s tests -v`.
- Sidecar path is the PDF's full filename plus `.md` (`X.pdf` → `X.pdf.md`, `Y.PDF` → `Y.PDF.md`).
- A sidecar is never rewritten while its `source_sha256` equals the manifest sha256.
- Generated files (`INDEX.md`, sidecars) contain no timestamps, so reruns produce no diff.
- `manifest.json` files are read-only for these scripts; curated data lives in `data/ird/circulars/metadata.json`.
- Public repo: no taxpayer-specific data anywhere; review `git diff --cached` before each commit.
- Work on branch `feat/corpus-text-index`. Commit messages are one line, Conventional Commits, no attribution trailers.
- Code comments only for a non-obvious why.

## Review Focus

1. Filenames with spaces or parentheses (`SET_Schedule_25_26(Tax_Credit)_E.pdf` exists): extraction must work and the index link must resolve. Test in Task 1 and Task 3.
2. A PDF that poppler cannot read (corrupt or encrypted): no partial sidecar is written, the run continues with other documents, and the exit code is non-zero. Test in Task 1.
3. A manifest entry whose file is missing or whose status is not `downloaded`: skipped by extraction, reported by `--check` only when status is `downloaded`. Test in Task 1.
4. Listing titles that do not match the modern pattern (`SEC 2011/06`, `Sec/2008/03.`, `Circular No. 2011/07`, no space before `[`): parsing returns nulls instead of raising. Test in Task 3.
5. `metadata.json` holding an entry whose PDF left the manifest, and titles containing `|`: the entry is kept and listed under an "Orphaned metadata" heading; pipes are escaped in table cells. Test in Task 3.

---

### Task 1: Shared corpus reader and text extraction

**Files:**
- Create: `scripts/corpus.py`
- Create: `scripts/extract_text.py`
- Test: `tests/test_extract_text.py`

**Interfaces:**
- Produces, in `scripts/corpus.py`:
  - `@dataclass(frozen=True) class Document` with fields `collection: str` (`"circulars"` or `"forms"`), `local_path: str` (as in the manifest), `pdf_path: Path`, `sha256: str`, `source_url: str`, `title: str`, `assessment_year: str | None` (forms only).
  - `iter_documents(data_root: Path) -> Iterator[Document]`: yields entries with status `downloaded` from `circulars/manifest.json` (`entries[]`, URL key `source_url`, paths relative to `data_root/circulars`) and `forms/individual/manifest.json` (`entries[].documents[]`, URL key `url`, paths relative to `data_root/forms/individual/<assessment_year>`).
  - `sidecar_path(pdf_path: Path) -> Path`.
- Produces, in `scripts/extract_text.py`:
  - `MIN_TEXT_CHARS = 100`
  - `needs_ocr(text: str) -> bool`: true when non-whitespace characters < `MIN_TEXT_CHARS`.
  - `extract_pages(pdf_path: Path, run=subprocess.run) -> list[tuple[str, str]]`: one `(method, text)` per page, method `"text"` or `"ocr"`. Raises `ExtractionError` on any tool failure.
  - `render_sidecar(doc: Document, pages: list[tuple[str, str]]) -> str`
  - `sidecar_sha(path: Path) -> str | None`: the `source_sha256` in an existing sidecar's front matter.
  - `main(argv: list[str] | None = None) -> int` with `--data-root` (default `data/ird`) and `--check`.

Sidecar format (exact):

```markdown
---
source: 2026/SEC_2026_E_07_E.pdf
source_url: https://www.ird.gov.lk/...
source_sha256: 4494ef...
pages: 3
ocr_pages: [1, 2, 3]
---

> Machine-extracted text for search. Confirm every figure against the PDF before relying on it.

## Page 1

...
```

- [ ] **Step 1: Create the branch**

Run: `git switch -c feat/corpus-text-index`

- [ ] **Step 2: Write failing tests in `tests/test_extract_text.py`**

Use `tempfile.TemporaryDirectory` fixtures holding a two-manifest `data_root`, and a fake `run` that returns canned stdout per command name.

- `test_iter_documents_reads_both_manifests`: one circular entry and one forms document yield two `Document`s with correct `pdf_path`, `source_url`, and `assessment_year == "2025-2026"` for the form; an entry with status `failed` is not yielded.
- `test_sidecar_path_appends_md`: `X.pdf` → `X.pdf.md`, `Y.PDF` → `Y.PDF.md`.
- `test_needs_ocr_threshold`: 99 non-space chars → `True`; 100 → `False`; whitespace is not counted.
- `test_extract_pages_uses_text_layer_then_ocr`: fake `pdfinfo` reports 2 pages; `pdftotext` returns 300 chars for page 1 and `""` for page 2; result is `[("text", ...), ("ocr", "OCR TEXT")]`, and `pdftoppm`/`tesseract` were called only for page 2.
- `test_extract_pages_passes_awkward_filename_unquoted`: PDF named `SET Schedule(Tax_Credit).pdf`; every recorded command is a list containing that exact path string as one element.
- `test_tool_failure_raises_and_writes_nothing`: fake `pdftotext` returns non-zero; `main` returns non-zero, no sidecar exists for that PDF, and the other document's sidecar was written.
- `test_render_sidecar_front_matter`: output starts with the front matter above, has `ocr_pages: [2]`, and contains `## Page 1` and `## Page 2`.
- `test_main_skips_current_sidecar`: sidecar with matching `source_sha256` exists; fake `run` records no calls and file mtime/content is unchanged.
- `test_main_regenerates_when_sha_differs`: sidecar with a different sha is rewritten.
- `test_check_reports_missing_and_stale`: `--check` returns 1 with one missing sidecar, 0 when all are current, and makes no tool calls. A `downloaded` entry whose PDF file is absent also returns 1.

- [ ] **Step 3: Run tests, confirm they fail**

Run: `python3 -m unittest tests.test_extract_text -v`
Expected: import error for `scripts/extract_text.py`.

- [ ] **Step 4: Implement `scripts/corpus.py` and `scripts/extract_text.py`**

Tool calls: `pdfinfo <pdf>` (parse `Pages:`); `pdftotext -layout -f N -l N <pdf> -`; for OCR, `pdftoppm -r 300 -f N -l N -png -singlefile <pdf> <tmp>/page` then `tesseract <tmp>/page.png - -l eng`. `main` collects failures, prints one line per document (`extracted` / `current` / `FAILED: reason`), and returns 1 if any failed. `extract_text.py` adds its own directory to `sys.path` before importing `corpus` so it works both as a script and under the test loader.

- [ ] **Step 5: Run tests, confirm they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: all pass, including the existing forms test.

- [ ] **Step 6: Commit**

```bash
git add scripts/corpus.py scripts/extract_text.py tests/test_extract_text.py
git commit -m "feat(corpus): add text sidecar extraction for IRD PDFs"
```

---

### Task 2: Generate sidecars for the existing corpus

**Files:**
- Create: `data/ird/**/<name>.pdf.md` (77 files)

**Interfaces:**
- Consumes: `scripts/extract_text.py` CLI from Task 1.
- Produces: a sidecar for every downloaded manifest entry.

- [ ] **Step 1: Run extraction in the background** (about 30–40 minutes)

Run: `python3 scripts/extract_text.py`
Expected: exit 0, one `extracted` line per document.

- [ ] **Step 2: Verify coverage**

Run: `python3 scripts/extract_text.py --check`
Expected: exit 0.

- [ ] **Step 3: Spot-check quality**

Open three sidecars against their PDFs: one OCR circular from 2026, one OCR circular from before 2016, and `forms/individual/2025-2026/return-pack/Asmt_IIT_001_2025_2026_E.pdf.md`. English body text must be readable and page headings must match PDF page numbers. If an older scan is unreadable, record its path in the task report; do not tune per-file.

- [ ] **Step 4: Confirm idempotence**

Run: `python3 scripts/extract_text.py && git status --short data | grep -v '^??' | wc -l`
Expected: `0` modified files.

- [ ] **Step 5: Commit**

```bash
git add data/ird
git commit -m "chore(ird): add extracted text sidecars for corpus"
```

---

### Task 3: Metadata sync and index generation

**Files:**
- Create: `scripts/build_index.py`
- Create: `data/ird/circulars/metadata.json` (stubs, generated)
- Create: `data/ird/INDEX.md` (generated)
- Test: `tests/test_build_index.py`

**Interfaces:**
- Consumes: `corpus.sidecar_path`, both manifests.
- Produces:
  - `TAX_TYPES = ("income_tax", "apit", "wht_ait", "vat", "svat", "sscl", "other")`
  - `TOPICS = ("instalments", "employment", "withholding", "returns_filing", "tin_registration", "reliefs_exemptions", "interest_dividends", "foreign_income", "penalties_interest", "administration", "indirect_tax", "other")`
  - `parse_title(title: str) -> dict` with keys `circular_no`, `revision`, `date`.
  - `sync_metadata(manifest: dict, metadata: dict) -> dict`: adds a stub for every manifest `local_path` missing from `metadata`; fills only `circular_no`/`revision`/`date` when they are null; never changes other fields; never removes entries.
  - `validate_metadata(metadata: dict, manifest: dict) -> list[str]`: errors for unknown `tax_types`/`topics`, and `revises`/`revised_by` values that are not manifest `local_path`s.
  - `render_index(circulars: dict, metadata: dict, forms: dict) -> str`
  - `main(argv=None) -> int` with `--data-root` and `--check` (exit 1 if `metadata.json` or `INDEX.md` on disk differs from what would be written, or validation fails).

Metadata entry (exact keys, stub values shown):

```json
"2026/SEC_2026_E_06_ReRiv_E.pdf": {
  "circular_no": "SEC/2026/E/06",
  "revision": "Re-Revised",
  "date": "2026-08-12",
  "subject": null,
  "summary": null,
  "tax_types": [],
  "topics": [],
  "assessment_years": null,
  "revises": [],
  "revised_by": [],
  "relevant_to_individuals": null,
  "reviewed": false
}
```

`assessment_years` is `null` (source does not say) or a list of `"YYYY/YYYY"` strings. `metadata.json` is written with `indent=2`, keys in manifest order, trailing newline.

Index layout: H1; a short "How to use" paragraph naming the lookup skill; the topic and tax-type vocabularies; `## Circulars` table, manifest order (newest first), columns `Circular | Date | Subject | Years | Topics | Status | Text | PDF | Source`; `## Individual forms` table by assessment year with columns `Year | Document | Text | PDF | Source`, where a year with no documents gets one row saying `not published on source page`; `## Orphaned metadata` only when non-empty. Status is `metadata pending` when `reviewed` is false, else `revised by <circular_no> (<revision>)` when `revised_by` is non-empty, else `latest in corpus`. Subject falls back to the manifest title while `subject` is null. Links are relative to `data/ird/` with spaces and parentheses percent-encoded.

- [ ] **Step 1: Write failing tests in `tests/test_build_index.py`**

- `test_parse_title_modern`: `"... - Circular No: SEC/2026/E/06 (Re-Revised) [12 August 2026]"` → `{"circular_no": "SEC/2026/E/06", "revision": "Re-Revised", "date": "2026-08-12"}`.
- `test_parse_title_no_space_before_bracket`: `"... Circular No: SEC/2026/E/04[08 June 2026]"` → `SEC/2026/E/04`, `revision` `None`, `2026-06-08`.
- `test_parse_title_abbreviated_month`: `"... Circular No. 2011/07 [09 Sep 2011] Illustrations to VAT Return"` → date `2011-09-09`.
- `test_parse_title_unrecognised_returns_nulls`: `"Some notice with no number"` → all three `None`, no exception. `"... Sec/2008/03. [05 Aug 2008]"` → date `2008-08-05`; `circular_no` is `None` or `"SEC/2008/03"`, never an exception.
- `test_sync_adds_stub_and_keeps_curated_fields`: existing entry with `subject="X"`, `reviewed=True` is unchanged; a new manifest path gains the stub above.
- `test_sync_keeps_orphans`: an entry absent from the manifest survives.
- `test_validate_rejects_unknown_topic_and_bad_revision_path`: returns two errors.
- `test_render_status_values`: three entries produce `metadata pending`, `revised by SEC/2026/E/06 (Re-Revised)`, and `latest in corpus`.
- `test_render_escapes_pipe_and_encodes_links`: title `A | B` renders `A \| B`; path `estimated-tax/SET_Schedule_25_26(Tax_Credit)_E.pdf` renders with `%28` and `%29`.
- `test_render_lists_orphans_and_pending_form_year`: orphan path appears under `## Orphaned metadata`; assessment year `2026-2027` with no documents renders `not published on source page`.
- `test_render_is_deterministic`: two calls return identical strings and the output contains no `retrieved_at_utc` value.
- `test_check_detects_stale_index`: after `main([])`, `main(["--check"])` returns 0; after editing `INDEX.md`, returns 1.

- [ ] **Step 2: Run tests, confirm they fail**

Run: `python3 -m unittest tests.test_build_index -v`
Expected: import error.

- [ ] **Step 3: Implement `scripts/build_index.py`**

- [ ] **Step 4: Run tests, confirm they pass**

Run: `python3 -m unittest discover -s tests -v`

- [ ] **Step 5: Generate stubs and index**

Run: `python3 scripts/build_index.py && python3 scripts/build_index.py --check`
Expected: exit 0; `metadata.json` has 69 entries; report how many have null `circular_no` or `date`.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_index.py tests/test_build_index.py data/ird/circulars/metadata.json data/ird/INDEX.md
git commit -m "feat(corpus): add circular metadata sync and corpus index"
```

---

### Task 4: Fill circular metadata

**Files:**
- Modify: `data/ird/circulars/metadata.json`
- Modify: `data/ird/INDEX.md` (regenerated)

**Interfaces:**
- Consumes: sidecars (Task 2), schema, `TOPICS`, `TAX_TYPES`, and `--check` (Task 3).

Rules for every entry:

- Read the sidecar; fill `subject` (short, the document's own subject line), `summary` (one or two plain sentences, no advice), `tax_types`, `topics`, `relevant_to_individuals`.
- `assessment_years`: only years the document itself states ("Applicable Period", "w.e.f. Y/A"). Otherwise leave `null`.
- `revises` / `revised_by`: set only when the document text says it amends or replaces another circular, or the official listing title carries `(Revised)` / `(Re-Revised)` for the same circular number. Set both directions.
- Fix `circular_no` / `date` where title parsing left them null.
- Before setting `reviewed: true`, open page 1 of the PDF itself and confirm `circular_no`, `date`, and `assessment_years`. If the scan is unreadable, leave `reviewed: false` and list the path in the task report.

- [ ] **Step 1: Fill entries for 2020–2026** (41 documents)
- [ ] **Step 2: Fill entries for 2008–2019** (28 documents)
- [ ] **Step 3: Regenerate and validate**

Run: `python3 scripts/build_index.py && python3 scripts/build_index.py --check`
Expected: exit 0, no validation errors.

- [ ] **Step 4: Check the known revision chain**

In `INDEX.md`, the three `SEC/2026/E/06` rows must read: original `revised by SEC/2026/E/06 (Revised)` or `(Re-Revised)`, Revised `revised by SEC/2026/E/06 (Re-Revised)`, Re-Revised `latest in corpus`.

- [ ] **Step 5: Commit**

```bash
git add data/ird/circulars/metadata.json data/ird/INDEX.md
git commit -m "chore(ird): add reviewed metadata for circulars"
```

---

### Task 5: Lookup skill and documentation

**Files:**
- Create: `.claude/skills/ird-lookup/SKILL.md`
- Modify: `AGENTS.md` (Evidence workflow step 2, Corpus maintenance)
- Modify: `README.md` (repository layout / usage section)

**Interfaces:**
- Consumes: `data/ird/INDEX.md`, sidecar naming, both script CLIs.

- [ ] **Step 1: Invoke `superpowers:writing-skills`, then write `SKILL.md`**

Front matter: `name: ird-lookup`; description starts with "Use when" and covers answering a Sri Lanka tax question, producing an estimate, or drafting filing data from this repository. Body, in this order:

1. Fix the assessment year; ask if it is missing and it changes the rule or form.
2. Read `data/ird/INDEX.md`. Shortlist by year and topic. Follow `revised by` to the latest version. Treat `metadata pending` rows as unknown relevance and include them.
3. Search and read the shortlisted `*.pdf.md` sidecars (grep across `data/ird/` for terms; read by `## Page N`).
4. For every rate, threshold, date, or formula used in the answer, open that page of the PDF and confirm it. OCR misreads digits.
5. Cite PDF path, page number, and the source URL from the index. Never cite a sidecar as evidence.
6. If the index and sidecars do not cover the question, say the corpus lacks it; do not fall back to memory.

Keep it under 60 lines; link to AGENTS.md for boundaries and privacy rather than repeating them.

- [ ] **Step 2: Update `AGENTS.md`**

In "Evidence workflow" step 2, add that agents start from `data/ird/INDEX.md` and the `.pdf.md` sidecars, and confirm figures in the PDF. In "Corpus maintenance", add a step: after any refresh run `python3 scripts/extract_text.py` and `python3 scripts/build_index.py`, and fill metadata for rows marked `metadata pending`.

- [ ] **Step 3: Update `README.md`**

Describe sidecars, `metadata.json`, `INDEX.md`, the two commands, and the local prerequisites (`poppler`, `tesseract`).

- [ ] **Step 4: Dry-run the skill**

Dispatch a fresh subagent with only: "In this repo, follow `.claude/skills/ird-lookup/SKILL.md`. For assessment year 2026/2027, which circular governs calculation of quarterly income tax instalments, and what page states the statutory due dates? Report the files you opened in order." Pass criteria: it opens `INDEX.md` first, lands on the Re-Revised `SEC/2026/E/06`, opens the PDF page to confirm, and cites PDF path, page, and URL. Fix the skill wording if it does not.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/ird-lookup/SKILL.md AGENTS.md README.md
git commit -m "docs(agents): add ird-lookup skill and index-first evidence workflow"
```

---

### Task 6: Weekly refresh integration

**Files:**
- Modify: `.github/workflows/refresh-ird.yml` (confirm the filename with `ls .github/workflows`)

**Interfaces:**
- Consumes: both script CLIs.

- [ ] **Step 1: Edit the workflow**

- After `setup-python`: a step running `sudo apt-get update && sudo apt-get install -y poppler-utils tesseract-ocr`.
- After "Fail on download errors" and before "Detect real changes": a step running `python3 scripts/extract_text.py` then `python3 scripts/build_index.py`.
- After that step: `python3 scripts/extract_text.py --check` and `python3 scripts/build_index.py --check`.
- Leave change detection and the commit step as they are; `git add data` already picks up sidecars, `metadata.json`, and `INDEX.md`.

- [ ] **Step 2: Verify the no-change path locally**

Run: `python3 scripts/extract_text.py && python3 scripts/build_index.py && git status --short data`
Expected: no output, so a week with no new documents still produces no commit.

- [ ] **Step 3: Validate workflow syntax**

Run: `ruby -ryaml -e 'YAML.load_file(ARGV[0]); puts "yaml ok"' .github/workflows/refresh-ird.yml`
Expected: `yaml ok`. A real run happens only after merge via `workflow_dispatch`; say so in the task report.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/refresh-ird.yml
git commit -m "ci: extract text and rebuild index in weekly IRD refresh"
```
