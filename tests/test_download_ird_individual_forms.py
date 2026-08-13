import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "download_ird_individual_forms.py"
SPEC = importlib.util.spec_from_file_location("individual_forms", SCRIPT_PATH)
individual_forms = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(individual_forms)


class IndividualFormsPlanTests(unittest.TestCase):
    def test_2025_2026_return_pack_has_all_required_documents(self):
        documents = individual_forms.documents_for_assessment_year("2025-2026")
        self.assertEqual(
            {document["id"] for document in documents},
            {
                "return_of_income",
                "return_schedules",
                "assets_and_liabilities",
                "return_completion_guide",
                "estimated_tax_statement",
                "estimated_tax_credit_schedule",
                "estimated_tax_guide",
                "apit_t10_certificate_amended",
            },
        )
        self.assertTrue(
            all(
                "2025_2026" in document["url"]
                or "25_26" in document["url"]
                or "2526" in document["url"]
                for document in documents
            )
        )

    def test_2026_2027_is_explicitly_pending_until_ird_publishes_forms(self):
        self.assertEqual(individual_forms.documents_for_assessment_year("2026-2027"), [])
        self.assertEqual(individual_forms.assessment_year_status("2026-2027"), "not_published_on_source_page")


if __name__ == "__main__":
    unittest.main()
