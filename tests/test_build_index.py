import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


import build_index  # noqa: E402

STUB = {
    "circular_no": None,
    "revision": None,
    "date": None,
    "subject": None,
    "summary": None,
    "tax_types": [],
    "topics": [],
    "assessment_years": None,
    "revises": [],
    "revised_by": [],
    "relevant_to_individuals": None,
    "reviewed": False,
    "reviewed_sha256": None,
}


def entry(path, title="T", sha="sha-"):
    return {"local_path": path, "title": title, "source_url": f"https://example.test/{path}", "status": "downloaded",
            "sha256": sha + path}


def manifest(*entries):
    return {"entries": list(entries)}


def meta(**overrides):
    return {**STUB, **overrides}


EMPTY_FORMS = {"entries": []}


class ParseTitleTests(unittest.TestCase):
    def test_parse_title_modern(self):
        title = "Circular to Taxpayers - Quarterly - Circular No: SEC/2026/E/06 (Re-Revised) [12 August 2026]"
        self.assertEqual(
            build_index.parse_title(title),
            {"circular_no": "SEC/2026/E/06", "revision": "Re-Revised", "date": "2026-08-12"},
        )

    def test_parse_title_no_space_before_bracket(self):
        result = build_index.parse_title("Circular to Withholding Agents - Circular No: SEC/2026/E/04[08 June 2026]")
        self.assertEqual(result["circular_no"], "SEC/2026/E/04")
        self.assertIsNone(result["revision"])
        self.assertEqual(result["date"], "2026-06-08")

    def test_parse_title_abbreviated_month(self):
        result = build_index.parse_title("Circular to VAT Registered Persons -Circular No. 2011/07 [09 Sep 2011] Illustrations to VAT Return")
        self.assertEqual(result["date"], "2011-09-09")
        self.assertEqual(result["circular_no"], "2011/07")

    def test_parse_title_unrecognised_returns_nulls(self):
        self.assertEqual(
            build_index.parse_title("Some notice with no number"),
            {"circular_no": None, "revision": None, "date": None},
        )
        result = build_index.parse_title("Implementation of VAT on Special Projects. Sec/2008/03. [05 Aug 2008]")
        self.assertEqual(result["date"], "2008-08-05")
        self.assertIn(result["circular_no"], (None, "SEC/2008/03"))

    def test_parse_title_odd_date_forms(self):
        self.assertEqual(build_index.parse_title("X - Circular No. SEC/2025/E/06 [19.11.2025]")["date"], "2025-11-19")
        self.assertEqual(build_index.parse_title("X - Circular No. SEC/2024/E/01 [04 January2023]")["date"], "2023-01-04")
        self.assertEqual(build_index.parse_title("X - Circular No: SEC/2022/E/06(Revised) [17 March 2023]")["revision"], "Revised")


class SyncTests(unittest.TestCase):
    def test_sync_adds_stub_and_keeps_curated_fields(self):
        existing = meta(subject="X", reviewed=True)
        mf = manifest(
            entry("a.pdf", "T - Circular No: SEC/2026/E/06 (Re-Revised) [12 August 2026]"),
            entry("b.pdf", "T - Circular No: SEC/2026/E/06 (Re-Revised) [12 August 2026]"),
        )
        result = build_index.sync_metadata(mf, {"a.pdf": existing})
        self.assertEqual(result["a.pdf"]["subject"], "X")
        self.assertTrue(result["a.pdf"]["reviewed"])
        self.assertEqual(result["a.pdf"]["circular_no"], "SEC/2026/E/06")
        self.assertEqual(
            result["b.pdf"],
            meta(circular_no="SEC/2026/E/06", revision="Re-Revised", date="2026-08-12"),
        )
        self.assertEqual(list(result["b.pdf"]), list(STUB))

    def test_sync_does_not_overwrite_filled_parsed_fields(self):
        mf = manifest(entry("a.pdf", "T - Circular No: SEC/2026/E/06 [12 August 2026]"))
        result = build_index.sync_metadata(mf, {"a.pdf": meta(circular_no="MANUAL")})
        self.assertEqual(result["a.pdf"]["circular_no"], "MANUAL")
        self.assertEqual(result["a.pdf"]["date"], "2026-08-12")

    def test_sync_adds_reviewed_sha_key_without_touching_other_fields(self):
        old = {k: v for k, v in meta(subject="X", reviewed=True).items() if k != "reviewed_sha256"}
        result = build_index.sync_metadata(manifest(entry("a.pdf")), {"a.pdf": old})
        self.assertIsNone(result["a.pdf"]["reviewed_sha256"])
        self.assertTrue(result["a.pdf"]["reviewed"])
        self.assertEqual(result["a.pdf"]["subject"], "X")

    def test_sync_keeps_existing_reviewed_sha(self):
        result = build_index.sync_metadata(
            manifest(entry("a.pdf")), {"a.pdf": meta(reviewed=True, reviewed_sha256="old")})
        self.assertEqual(result["a.pdf"]["reviewed_sha256"], "old")
        self.assertTrue(result["a.pdf"]["reviewed"])

    def test_sync_keeps_orphans(self):
        result = build_index.sync_metadata(manifest(entry("a.pdf")), {"gone.pdf": meta(subject="old")})
        self.assertEqual(result["gone.pdf"]["subject"], "old")
        self.assertEqual(list(result), ["a.pdf", "gone.pdf"])


class ValidateTests(unittest.TestCase):
    def test_validate_rejects_unknown_topic_and_bad_revision_path(self):
        mf = manifest(entry("a.pdf"))
        errors = build_index.validate_metadata(
            {"a.pdf": meta(topics=["nonsense"], tax_types=["vat"], revised_by=["missing.pdf"])},
            mf,
        )
        self.assertEqual(len(errors), 2)

    def test_validate_accepts_known_values(self):
        mf = manifest(entry("a.pdf"), entry("b.pdf"))
        metadata = {"a.pdf": meta(topics=["employment"], tax_types=["apit"], revises=["b.pdf"]), "b.pdf": meta()}
        self.assertEqual(build_index.validate_metadata(metadata, mf), [])


    def test_validate_accepts_orphaned_metadata_key_as_revision_target(self):
        mf = manifest(entry("a.pdf"))
        metadata = {"a.pdf": meta(revised_by=["gone.pdf"]), "gone.pdf": meta()}
        self.assertEqual(build_index.validate_metadata(metadata, mf), [])

    def test_validate_rejects_path_that_is_neither_manifest_nor_metadata(self):
        mf = manifest(entry("a.pdf"))
        errors = build_index.validate_metadata({"a.pdf": meta(revises=["nowhere.pdf"])}, mf)
        self.assertEqual(len(errors), 1)

    def test_validate_rejects_non_list_fields(self):
        mf = manifest(entry("a.pdf"))
        for field in ("tax_types", "topics", "revises", "revised_by"):
            for bad in (None, "vat"):
                errors = build_index.validate_metadata({"a.pdf": meta(**{field: bad})}, mf)
                self.assertEqual(len(errors), 1, (field, bad))

    def test_validate_assessment_years(self):
        mf = manifest(entry("a.pdf"))
        for good in (None, [], ["2023/2024", "2025/2026"]):
            self.assertEqual(build_index.validate_metadata({"a.pdf": meta(assessment_years=good)}, mf), [])
        for bad in ("2023/2024", ["2023-2024"], ["2023/2025"], [2023], ["2023/2024 "]):
            errors = build_index.validate_metadata({"a.pdf": meta(assessment_years=bad)}, mf)
            self.assertEqual(len(errors), 1, bad)


class RenderTests(unittest.TestCase):
    def test_render_status_values(self):
        mf = manifest(entry("a.pdf"), entry("b.pdf"), entry("c.pdf"))
        metadata = {
            "a.pdf": meta(),
            "b.pdf": meta(reviewed=True, reviewed_sha256="sha-b.pdf", revised_by=["a.pdf"]),
            "c.pdf": meta(reviewed=True, reviewed_sha256="sha-c.pdf"),
        }
        metadata["a.pdf"]["circular_no"] = "SEC/2026/E/06"
        metadata["a.pdf"]["revision"] = "Re-Revised"
        out = build_index.render_index(mf, metadata, EMPTY_FORMS)
        self.assertIn("metadata pending", out)
        self.assertIn("latest in corpus", out)
        self.assertIn("revised by SEC/2026/E/06 (Re-Revised)", out)

    def test_render_status_requires_matching_reviewed_sha(self):
        mf = manifest(entry("a.pdf"), entry("b.pdf"), entry("c.pdf"))
        metadata = {
            "a.pdf": meta(reviewed=True, reviewed_sha256="sha-a.pdf"),
            "b.pdf": meta(reviewed=True, reviewed_sha256="different"),
            "c.pdf": meta(reviewed=True, reviewed_sha256=None),
        }
        rows = build_index.render_index(mf, metadata, EMPTY_FORMS).splitlines()
        rows = [r for r in rows if "circulars/" in r]
        self.assertIn("latest in corpus", next(r for r in rows if "circulars/a.pdf)" in r))
        self.assertIn("metadata pending", next(r for r in rows if "circulars/b.pdf)" in r))
        self.assertIn("metadata pending", next(r for r in rows if "circulars/c.pdf)" in r))

    def test_render_revised_by_without_revision_has_no_parenthetical(self):
        mf = manifest(entry("a.pdf"), entry("b.pdf"))
        metadata = {
            "a.pdf": meta(circular_no="SEC/2026/E/01"),
            "b.pdf": meta(reviewed=True, reviewed_sha256="sha-b.pdf", revised_by=["a.pdf"]),
        }
        out = build_index.render_index(mf, metadata, EMPTY_FORMS)
        self.assertIn("revised by SEC/2026/E/01 |", out)
        self.assertNotIn("(original)", out)

    def test_render_how_to_use_says_years_never_exclude(self):
        out = build_index.render_index(manifest(), {}, EMPTY_FORMS)
        self.assertIn("Use Years only to include a row, never to exclude one.", out)
        self.assertIn("A blank Years cell means the document names no year of assessment.", out)

    def test_render_escapes_pipe_and_encodes_links(self):
        mf = manifest(entry("estimated-tax/SET_Schedule_25_26(Tax_Credit)_E.pdf", "A | B"))
        out = build_index.render_index(mf, {}, EMPTY_FORMS)
        self.assertIn("A \\| B", out)
        self.assertIn("circulars/estimated-tax/SET_Schedule_25_26%28Tax_Credit%29_E.pdf", out)
        self.assertIn("%28Tax_Credit%29_E.pdf.md", out)

    def test_render_lists_orphans_and_pending_form_year(self):
        forms = {"entries": [{"assessment_year": "2026-2027", "status": "pending", "documents": []}]}
        out = build_index.render_index(manifest(), {"orphan.pdf": meta()}, forms)
        self.assertIn("## Orphaned metadata", out)
        self.assertIn("orphan.pdf", out)
        self.assertIn("not published on source page", out)

    def test_render_omits_orphans_section_when_empty(self):
        self.assertNotIn("Orphaned", build_index.render_index(manifest(entry("a.pdf")), {"a.pdf": meta()}, EMPTY_FORMS))

    def test_render_form_documents_link_into_year_directory(self):
        forms = {"entries": [{"assessment_year": "2025-2026", "documents": [
            {"title": "Return", "url": "https://example.test/r.pdf", "local_path": "return-pack/r.pdf", "status": "downloaded"}]}]}
        out = build_index.render_index(manifest(), {}, forms)
        self.assertIn("forms/individual/2025-2026/return-pack/r.pdf.md", out)

    def test_render_is_deterministic(self):
        mf = manifest(entry("a.pdf"))
        mf["entries"][0]["retrieved_at_utc"] = "2026-11-27T07:57:48+00:00"
        first = build_index.render_index(mf, {"a.pdf": meta()}, EMPTY_FORMS)
        self.assertEqual(first, build_index.render_index(mf, {"a.pdf": meta()}, EMPTY_FORMS))
        self.assertNotIn("2026-11-27T07", first)


class MainTests(unittest.TestCase):
    def test_check_fails_on_invalid_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "circulars").mkdir()
            (root / "forms" / "individual").mkdir(parents=True)
            (root / "circulars" / "manifest.json").write_text(json.dumps(manifest(entry("a.pdf"))), encoding="utf-8")
            (root / "forms" / "individual" / "manifest.json").write_text(json.dumps(EMPTY_FORMS), encoding="utf-8")
            (root / "circulars" / "metadata.json").write_text(
                json.dumps({"a.pdf": meta(topics=["nonsense"])}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build_index.main(["--data-root", str(root), "--check"]), 1)

    def test_check_detects_stale_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "circulars").mkdir()
            (root / "forms" / "individual").mkdir(parents=True)
            (root / "circulars" / "manifest.json").write_text(
                json.dumps(manifest(entry("2026/a.pdf", "T - Circular No: SEC/2026/E/01 [23 March 2026]"))), encoding="utf-8")
            (root / "forms" / "individual" / "manifest.json").write_text(json.dumps(EMPTY_FORMS), encoding="utf-8")
            args = ["--data-root", str(root)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build_index.main(args), 0)
                self.assertEqual(build_index.main(args + ["--check"]), 0)
                index = root / "INDEX.md"
                index.write_text(index.read_text(encoding="utf-8") + "\nedit\n", encoding="utf-8")
                self.assertEqual(build_index.main(args + ["--check"]), 1)


if __name__ == "__main__":
    unittest.main()
