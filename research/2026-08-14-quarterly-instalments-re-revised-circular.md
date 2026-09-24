# 14 August 2026 check: quarterly-income-tax-instalments circular

Checked: 14 August 2026 (Asia/Colombo)  
Assessment year: 2026/2027

## Conclusion

The claimed change is real, but the official document is **not dated 14 August**.  The IRD circular index now lists **Circular No. SEC/2026/E/06 (Re-Revised), dated 12 August 2026**, titled *Circular to Taxpayers - Calculating Quarterly Income Tax Instalments w.e.f. Y/A 2026/2027*.  It expressly amends the 3 August original and 6 August revised circulars.

It **does not move the first quarterly income-tax instalment payment due date**: it remains **on or before 15 August 2026**.  The material change for the immediate deadline is the supporting-attachment process: the earlier revised circular required the attachments by 15 August; the re-revised circular permits them until **30 November 2026**, and introduces the RAMIS upload route shown in the screenshot.

## What changed

| Item | 6 August revised circular | 12 August re-revised circular | Effect |
| --- | --- | --- | --- |
| First instalment payment | On or before 15 August of the assessment year | Same | The payment deadline remains 15 August 2026. |
| Required attachments | Submit to CDMU, Metro or relevant Regional Office by 15 August | Submit by 30 November 2026 | Attachment deadline is extended; this is separate from paying the tax instalment. |
| Attachment channel | Physical/office submission only stated | RAMIS upload permitted; CDMU/Metro/Regional Office remains an option | Taxpayers can use the online process below. |
| Scope stated in title/body | 2026/2027 and subsequent assessment years | 2026/2027 | This version is expressly framed for 2026/2027. |

## Who this concerns

This is a circular to **income-tax instalment payers** for Y/A 2026/2027, including individuals, partnerships, companies and other listed taxpayers.  A taxpayer who can use the standard prior-year method has no circular-specific declaration attachment to file.  The attachment/declaration applies where the taxpayer uses an alternative basis (for example, no prior taxable income, lower expected income, or a newly registered taxpayer).

The circular also says that an individual whose income is solely employment income subject to APIT does not need quarterly instalments or the credit schedule.  An employee with employment income plus rent/interest subject to AIT is likewise outside the payment and credit-schedule requirement if APIT/AIT covers the remaining current-year liability.  These conclusions depend on the taxpayer's actual income and credits.

## Payment and online attachment instructions

1. **Pay the first quarterly instalment by 15 August 2026** if it is payable.  The circular's formula is `(A - C) / B`, where for the first instalment `B = 4`; `A` is the preceding year's gross tax before tax credits and `C` is tax already withheld/paid for the current assessment year before the due date.
   The IRD's 2026 Tax Calendar identifies the individual-income-tax payment as tax type **05**, payment period **26271**; it also separately lists the Y/A 2026/2027 Statement of Estimated Tax (SET) as period **2627**.  Confirm the payment type and period presented by the bank/portal against the taxpayer's own assessment before authorising payment.
2. For a required **Attachment 1** declaration, upload it in RAMIS while filing the **Y/A 2025/2026 Return of Income**: `Upload Supporting Documents` -> `Supporting Documents` -> `Other Relevant Documents`.
3. Name the file `TIN_2627_INSAttachment1` (for example, `111122222_2627_INSAttachment1`).  Where applicable use `INSAttachment1_Revised` or `INSAttachment2`; Attachment 1 and its revised version may both be submitted on the same date.
4. The attachment may instead be delivered manually to CDMU, the Metro office, or the relevant Regional Office.  The attachment deadline is **30 November 2026**.

The circular says payment instructions will be provided separately as taxpayer assistance.  It does not say that uploading the attachment itself makes the payment.  The official upcoming-due-dates page was checked but currently displays 2024 entries, so it is not reliable corroboration for the 2026 due date.

For payment, the IRD's Online Tax Payment Platform (OTPP) says its member banks accept tax payments through CEFTS channels - internet banking, mobile banking, ATM or over the counter - with real-time crediting, subject to banking regulations.  This is a payment route, not the RAMIS attachment upload route.

## Evidence and provenance

- Current official index: [IRD Circulars listing](https://www.ird.gov.lk/en/publications/sitepages/Circulars.aspx?menuid=1506). It lists the re-revised document as 12 August 2026 and the earlier 6 August revision.
- New official source document: [SEC/2026/E/06 (Re-Revised), 12 August 2026](https://www.ird.gov.lk/en/publications/Circulars_Circulars/SEC_2026_E_06_ReRiv_E.pdf). Relevant material: page 1 (date, supersession context, statutory due dates and formula); pages 8-10 (alternative bases and eligibility); page 11 (submission deadline and RAMIS filename/process); Attachments 1-2 (pages 12-16).
- Earlier official document for the comparison: [SEC/2026/E/06 (Revised), 6 August 2026](https://www.ird.gov.lk/en/publications/Circulars_Circulars/SEC_2026_E_06_Riv_E.pdf), page 10 (then-required attachment submission by 15 August).
- Local corpus snapshot before the new document: [data/ird/circulars/manifest.json](../data/ird/circulars/manifest.json), retrieved 13 August 2026, records the 6 August revision but not the 12 August re-revision.  The archived local comparison copy is [data/ird/circulars/2026/SEC_2026_E_06_Riv_E.pdf](../data/ird/circulars/2026/SEC_2026_E_06_Riv_E.pdf).
- Official due-dates page checked on 14 August: [IRD Upcoming Due Dates](https://www.ird.gov.lk/en/SitePages/UpcomingDueDatesList.aspx?menuid=1417). It currently exposes outdated 2024 entries.
- Official corroboration of payment date/type/period: [IRD Tax Calendar 2026](https://www.ird.gov.lk/en/publications/Tax%20Calendar_Documents/Tax_Calendar_2026_E.pdf), page 4 (15 August 2026, income-tax first instalment for Y/A 2026/2027; individual type 05, period 26271).
- Official payment-channel guidance: [IRD Online Tax Payment Platform](https://www.ird.gov.lk/en/publications/SitePages/Online_Pay_OTP.aspx?menuid=141601).

The new 12 August PDF was retrieved temporarily for inspection from the official URL; SHA-256: `4889d4b3647ef0d0d397e1669edd8db7c17611f27ea75087d7e73e2c5b98de23`.  It was not added to `data/ird/` or its manifest in this research task, so the established archive remains unchanged pending a normal source-refresh/verification run.
