# Sri Lanka Individual Tax Knowledge Base

An open, source-traceable archive of official Sri Lanka **Inland Revenue Department
(IRD)** circulars and individual income-tax forms, with checksummed manifests and
scripts to refresh them. Built as an evidence base for AI tax-advisor agents and for
anyone who wants IRD material in one auditable place.

> **Disclaimer:** Not legal or tax advice, and not affiliated with or endorsed by the
> IRD. Documents are copies of public IRD publications; always confirm against
> [ird.gov.lk](https://www.ird.gov.lk) before relying on them.

## Purpose

The knowledge base supports:

- source-backed guidance on Sri Lanka individual income tax;
- estimated income-tax and quarterly-instalment calculations;
- APIT, AIT/WHT, employment income, interest-income, and senior-citizen refund
  scenarios where the official sources cover them; and
- draft return data that a taxpayer can review before filing through IRD systems.

It is not a substitute for a current legal determination, professional advice, or
submission to IRD. Every answer and calculation must identify its assessment year
and the official material supporting it.

## Source collections

| Collection | Contents | Source of truth |
| --- | --- | --- |
| `data/ird/circulars/` | IRD circular PDFs, grouped by document year | `manifest.json` |
| `data/ird/forms/individual/` | Individual filing forms grouped by assessment year | `manifest.json` |
| `research/` | Official-source inventories and retrieval notes | individual inventory files |
| `scripts/` | Repeatable download/verification collectors | script help and manifests |

The original official URL, retrieval timestamp, file size, and SHA-256 digest are
recorded in each collection manifest. PDFs are evidence snapshots, not proof that
a historical rule remains in force.

## Current coverage

- Circulars: 69 official IRD circulars from 2008–2026 (latest: SEC/2026/E/07).
- Individual forms: complete 2025/2026 return pack plus estimated-tax and APIT/T.10
  material available on the IRD forms page at collection time.
- 2026/2027 individual return forms: not yet published on the official forms page;
  the directory is deliberately marked pending rather than populated with prior-year
  forms.

## Refreshing collections

Run from the repository root:

```sh
python3 scripts/download_ird_circulars.py
python3 scripts/download_ird_circulars.py --verify
python3 scripts/download_ird_individual_forms.py
```

After a refresh, inspect each manifest for failed downloads and update the source
inventory if IRD changed the page structure or published a new assessment-year pack.

## Working with an advisor agent

Read [AGENTS.md](AGENTS.md) before using this repository to answer a tax question,
perform a calculation, or extend the corpus. It defines the evidence workflow,
assessment-year discipline, and safe hand-off rules for the future agent.
