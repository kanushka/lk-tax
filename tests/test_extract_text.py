import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


import corpus  # noqa: E402
import extract_text  # noqa: E402

SHA_A = "a" * 64
SHA_B = "b" * 64
LONG_TEXT = "x" * 300


class FakeRun:
    def __init__(self, pages=2, texts=None, fail=None):
        self.pages = pages
        self.texts = texts or {}
        self.fail = fail or set()
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        tool = cmd[0]
        if tool in self.fail:
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")
        if tool == "pdfinfo":
            return SimpleNamespace(returncode=0, stdout=f"Title: t\nPages:          {self.pages}\n", stderr="")
        if tool == "pdftotext":
            page = int(cmd[cmd.index("-f") + 1])
            return SimpleNamespace(returncode=0, stdout=self.texts.get(page, ""), stderr="")
        if tool == "tesseract":
            return SimpleNamespace(returncode=0, stdout="OCR TEXT", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


def make_root(tmp, circular_name="c.pdf", form_name="f.pdf", extra_entries=()):
    root = Path(tmp)
    (root / "circulars" / "2026").mkdir(parents=True)
    (root / "forms" / "individual" / "2025-2026" / "return-pack").mkdir(parents=True)
    (root / "circulars" / "2026" / circular_name).write_bytes(b"%PDF")
    (root / "forms" / "individual" / "2025-2026" / "return-pack" / form_name).write_bytes(b"%PDF")
    circulars = {
        "entries": [
            {
                "title": "Circ",
                "source_url": "https://example.test/c.pdf",
                "local_path": f"2026/{circular_name}",
                "status": "downloaded",
                "sha256": SHA_A,
            },
            {
                "title": "Bad",
                "source_url": "https://example.test/bad.pdf",
                "local_path": "2026/bad.pdf",
                "status": "failed",
            },
            *extra_entries,
        ]
    }
    forms = {
        "entries": [
            {
                "assessment_year": "2025-2026",
                "status": "published",
                "documents": [
                    {
                        "id": "f",
                        "title": "Form",
                        "url": "https://example.test/f.pdf",
                        "local_path": f"return-pack/{form_name}",
                        "status": "downloaded",
                        "sha256": SHA_B,
                    }
                ],
            }
        ]
    }
    (root / "circulars" / "manifest.json").write_text(json.dumps(circulars))
    (root / "forms" / "individual" / "manifest.json").write_text(json.dumps(forms))
    return root


def run_main(argv, run):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = extract_text.main(argv, run=run)
    return code, out.getvalue()


class CorpusTests(unittest.TestCase):
    def test_iter_documents_reads_both_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            docs = list(corpus.iter_documents(root))
        self.assertEqual(len(docs), 2)
        circular = next(d for d in docs if d.collection == "circulars")
        form = next(d for d in docs if d.collection == "forms")
        self.assertEqual(circular.pdf_path, root / "circulars" / "2026" / "c.pdf")
        self.assertEqual(circular.source_url, "https://example.test/c.pdf")
        self.assertEqual(circular.local_path, "2026/c.pdf")
        self.assertEqual(circular.sha256, SHA_A)
        self.assertIsNone(circular.assessment_year)
        self.assertEqual(form.assessment_year, "2025-2026")
        self.assertEqual(form.source_url, "https://example.test/f.pdf")
        self.assertEqual(
            form.pdf_path, root / "forms" / "individual" / "2025-2026" / "return-pack" / "f.pdf"
        )

    def test_sidecar_path_appends_md(self):
        self.assertEqual(corpus.sidecar_path(Path("a/X.pdf")), Path("a/X.pdf.md"))
        self.assertEqual(corpus.sidecar_path(Path("a/Y.PDF")), Path("a/Y.PDF.md"))


class ExtractTests(unittest.TestCase):
    def test_needs_ocr_threshold(self):
        self.assertTrue(extract_text.needs_ocr("a" * 99))
        self.assertFalse(extract_text.needs_ocr("a" * 100))
        self.assertTrue(extract_text.needs_ocr("a" * 99 + " \n\t " * 50))

    def test_extract_pages_uses_text_layer_then_ocr(self):
        fake = FakeRun(pages=2, texts={1: LONG_TEXT})
        pages = extract_text.extract_pages(Path("doc.pdf"), run=fake)
        self.assertEqual(pages, [("text", LONG_TEXT), ("ocr", "OCR TEXT")])
        ocr_calls = [c for c in fake.calls if c[0] in ("pdftoppm", "tesseract")]
        self.assertEqual([c[0] for c in ocr_calls], ["pdftoppm", "tesseract"])
        self.assertEqual(ocr_calls[0][ocr_calls[0].index("-f") + 1], "2")

    def test_extract_pages_passes_awkward_filename_unquoted(self):
        name = "SET Schedule(Tax_Credit).pdf"
        fake = FakeRun(pages=1)
        extract_text.extract_pages(Path("dir") / name, run=fake)
        self.assertTrue(fake.calls)
        for call in fake.calls:
            self.assertIsInstance(call, list)
            if call[0] != "tesseract":
                self.assertIn(str(Path("dir") / name), call)

    def test_tool_failure_raises(self):
        fake = FakeRun(fail={"pdftotext"})
        with self.assertRaises(extract_text.ExtractionError):
            extract_text.extract_pages(Path("doc.pdf"), run=fake)

    def test_tool_failure_writes_nothing_for_that_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp, circular_name="bad.pdf")

            def run(cmd, **kwargs):
                if cmd[0] == "pdftotext" and cmd[-2].endswith("bad.pdf"):
                    return SimpleNamespace(returncode=1, stdout="", stderr="boom")
                return FakeRun(pages=1, texts={1: LONG_TEXT})(cmd, **kwargs)

            code, out = run_main(["--data-root", str(root)], run)
            self.assertNotEqual(code, 0)
            self.assertIn("FAILED", out)
            self.assertFalse((root / "circulars" / "2026" / "bad.pdf.md").exists())
            self.assertTrue((root / "forms" / "individual" / "2025-2026" / "return-pack" / "f.pdf.md").exists())

    def test_render_sidecar_front_matter(self):
        doc = corpus.Document(
            collection="circulars",
            local_path="2026/c.pdf",
            pdf_path=Path("c.pdf"),
            sha256=SHA_A,
            source_url="https://example.test/c.pdf",
            title="Circ",
            assessment_year=None,
        )
        text = extract_text.render_sidecar(doc, [("text", "first"), ("ocr", "second")])
        self.assertTrue(
            text.startswith(
                "---\n"
                "source: 2026/c.pdf\n"
                "source_url: https://example.test/c.pdf\n"
                f"source_sha256: {SHA_A}\n"
                "pages: 2\n"
                "ocr_pages: [2]\n"
                "---\n\n"
                "> Machine-extracted text for search. Confirm every figure against the PDF before relying on it.\n\n"
                "## Page 1\n\nfirst\n"
            )
        )
        self.assertIn("## Page 2\n\nsecond\n", text)

    def test_sidecar_sha_reads_front_matter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.pdf.md"
            self.assertIsNone(extract_text.sidecar_sha(path))
            path.write_text(f"---\nsource: a\nsource_sha256: {SHA_A}\n---\n")
            self.assertEqual(extract_text.sidecar_sha(path), SHA_A)

    def test_main_skips_current_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            fake = FakeRun(pages=1, texts={1: LONG_TEXT})
            self.assertEqual(run_main(["--data-root", str(root)], fake)[0], 0)
            sidecar = root / "circulars" / "2026" / "c.pdf.md"
            before = (sidecar.read_text(), sidecar.stat().st_mtime_ns)
            second = FakeRun()
            code, out = run_main(["--data-root", str(root)], second)
            self.assertEqual(code, 0)
            self.assertEqual(second.calls, [])
            self.assertEqual((sidecar.read_text(), sidecar.stat().st_mtime_ns), before)
            self.assertIn("current", out)

    def test_main_regenerates_when_sha_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            sidecar = root / "circulars" / "2026" / "c.pdf.md"
            sidecar.write_text(f"---\nsource_sha256: {SHA_B}\n---\nold\n")
            fake = FakeRun(pages=1, texts={1: LONG_TEXT})
            code, _ = run_main(["--data-root", str(root)], fake)
            self.assertEqual(code, 0)
            self.assertIn(f"source_sha256: {SHA_A}", sidecar.read_text())

    def test_check_reports_missing_and_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            fake = FakeRun()
            code, _ = run_main(["--data-root", str(root), "--check"], fake)
            self.assertEqual(code, 1)
            self.assertEqual(fake.calls, [])

            run_main(["--data-root", str(root)], FakeRun(pages=1, texts={1: LONG_TEXT}))
            code, _ = run_main(["--data-root", str(root), "--check"], fake)
            self.assertEqual(code, 0)
            self.assertEqual(fake.calls, [])

            (root / "circulars" / "2026" / "c.pdf.md").write_text(f"---\nsource_sha256: {SHA_B}\n---\n")
            code, _ = run_main(["--data-root", str(root), "--check"], fake)
            self.assertEqual(code, 1)

    def test_missing_pdf_is_reported_and_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            (root / "circulars" / "2026" / "c.pdf").unlink()
            fake = FakeRun(pages=1, texts={1: LONG_TEXT})
            code, out = run_main(["--data-root", str(root)], fake)
            self.assertEqual(code, 1)
            self.assertIn("MISSING", out)
            self.assertTrue((root / "forms" / "individual" / "2025-2026" / "return-pack" / "f.pdf.md").exists())
            code, _ = run_main(["--data-root", str(root), "--check"], fake)
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
