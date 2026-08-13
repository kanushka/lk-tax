# Sri Lanka IRD circulars

This directory is populated from the official Inland Revenue Department circulars
listing by `scripts/download_ird_circulars.py`.

- Source listing: <https://www.ird.gov.lk/en/publications/sitepages/Circulars.aspx?menuid=1506>
- PDF folders: year inferred from the official circular number or listing label
- `manifest.json`: title, official source URL, local path, retrieval timestamp,
  download status, file size, and SHA-256 checksum

Run from the repository root:

```sh
python3 scripts/download_ird_circulars.py
```

Verify the local PDFs have not changed:

```sh
python3 scripts/download_ird_circulars.py --verify
```

The manifest is the source of truth for the collection; do not infer tax rules
solely from an archived PDF without checking whether the IRD has later replaced
or amended it.
