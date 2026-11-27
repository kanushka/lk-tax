---
name: ird-lookup
description: Use when answering a Sri Lanka tax question, producing a tax estimate, or drafting filing data from this repository's IRD circulars and forms, including finding which circular or form applies to an assessment year.
---

# IRD lookup

Find evidence through the index and text sidecars. The PDFs are the evidence; sidecars
(`X.pdf` -> `X.pdf.md`) are for finding only. Boundaries and privacy rules are in
[AGENTS.md](../../../AGENTS.md).

## Steps

1. Fix the assessment year. If it is missing and changes the rule or form, ask the
   user before searching.
2. Read `data/ird/INDEX.md`. Shortlist rows by Topics and Date. Use Years only to
   include a row, never to exclude one: a blank Years cell means the document names no
   year of assessment, and Years is not an end date, so a circular stays applicable to
   later years until a later one revises it. When a row says
   `revised by <circular_no>` (with `(<revision>)` when the later one is a revision),
   follow it to the latest version. Treat
   `metadata pending` rows as unknown relevance and include them in the shortlist.
3. Search and read the shortlisted `*.pdf.md` sidecars. Grep across `data/ird/` for
   terms, then read by `## Page N` section.
4. For every rate, threshold, date, or formula used in the answer, open that page of
   the PDF and confirm it. OCR misreads digits.
5. Cite the PDF path, page number, and the source URL from the index. Never cite a
   sidecar as evidence.
6. If the index and sidecars do not cover the question, say the corpus lacks it. Do
   not fall back to memory.

## Commands

```sh
grep -rniE "instalment|due date" data/ird --include='*.pdf.md'
```

The `grep` terms are examples; use the terms of the actual question.
