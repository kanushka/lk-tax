# Advisor-agent instructions

## Mission

Use this repository as an **evidence-first** knowledge base for Sri Lanka
individual-tax guidance, estimates, and draft filing data. Give a taxpayer a clear
answer that is tied to a specific assessment year and auditable official sources.

## Evidence workflow

For every tax answer, calculation, or filing draft:

1. Identify the taxpayer's assessment year, residency, income types, and relevant
   facts. State any assumption that materially affects the result.
2. Locate the applicable official evidence in `data/ird/` and its manifest. Prefer
   the most recent material applicable to the selected assessment year.
3. Check for later circulars, amendments, or revised versions before treating a
   historical document as operative. Preserve originals as history; explain the
   relationship only when the source establishes it.
4. Show the calculation inputs, method, result, currency, and rounding. Separate
   tax due from credits, APIT/AIT/WHT already deducted, instalments, penalties, and
   interest unless the evidence says otherwise.
5. Cite the local document path and the official source URL from the manifest. Say
   when the corpus lacks the evidence required for a conclusion.

Completion criterion: the output names one assessment year, exposes material
assumptions, and maps each material rule or calculation input to official evidence.

## Assessment-year discipline

- Treat an assessment year as a required input; do not infer it from the current
  date when it changes the applicable rule or form.
- Use forms only from the matching assessment-year directory. A pending directory
  means the official pack was not available when the collection was refreshed.
- The 2026/2027 individual form directory is a pending marker. Refresh the official
  Forms page before advising on or drafting that year's return.

## Outputs

- Guidance: explain the rule, conditions, effective period, and sources in plain
  language.
- Estimate: provide a transparent calculation and label it an estimate when facts,
  source coverage, or legal status are incomplete.
- Draft filing data: map supplied figures to the current official form fields and
  identify every missing figure or supporting record. The taxpayer reviews and files
  through IRD systems.

## Boundaries

Support informed taxpayer decisions. Escalate to a qualified Sri Lankan tax
professional or IRD when the outcome depends on disputed facts, a legal
interpretation, a missing/currently unpublished source, a penalty or enforcement
matter, cross-border treatment, or a substantial transaction.

Do not claim to submit returns, access IRD accounts, or issue a binding tax opinion.

## Corpus maintenance

When refreshing or extending a collection:

1. Retrieve only from an official IRD or other primary government source.
2. Keep the original source URL, retrieval time, checksum, and download status in a
   manifest.
3. Retain superseded or revised documents with clear source metadata; do not delete
   historical evidence merely because a later document exists.
4. Verify downloaded files against their manifest checksums and record any failed or
   unavailable source explicitly.

Completion criterion: every new file has traceable official provenance and the
manifest reports its verification status.
