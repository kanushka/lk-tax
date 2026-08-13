# Sri Lanka IRD forms

This archive holds individual income-tax filing forms separately from the circulars.

Run the collector from the repository root:

```sh
python3 scripts/download_ird_individual_forms.py
```

It downloads only the individual 2025/2026 form pack currently published by the
official Forms and Returns page. The `2026-2027` directory is deliberately kept
as a pending marker until the IRD publishes that year's forms.

Official source: <https://www.ird.gov.lk/en/Downloads/SitePages/Forms.aspx?menuid=1603>
