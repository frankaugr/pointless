import unittest

from pointless_revision.categories import CATEGORIES
from pointless_revision.export import build_payloads


class CatalogTests(unittest.TestCase):
    def test_core_category_pack_is_present(self):
        self.assertGreaterEqual(len(CATEGORIES), 9)
        for slug in [
            "chemical-elements",
            "countries",
            "world-capitals",
            "uk-prime-ministers",
            "us-presidents",
            "us-states",
            "us-state-capitals",
            "uk-cities",
            "english-british-monarchs",
        ]:
            self.assertIn(slug, CATEGORIES)

    def test_expected_counts_validate(self):
        _index, payloads = build_payloads()
        self.assertEqual(payloads["chemical-elements"]["n_answers"], 118)
        self.assertEqual(payloads["countries"]["n_answers"], 195)
        self.assertEqual(payloads["us-state-capitals"]["n_answers"], 50)
        self.assertEqual(payloads["uk-cities"]["n_answers"], 76)

    def test_bogus_prime_minister_is_gone(self):
        _index, payloads = build_payloads()
        names = {answer["name"] for answer in payloads["uk-prime-ministers"]["answers"]}
        self.assertNotIn("Basil Feilding, 6th Earl of Denbigh", names)
        self.assertIn("Keir Starmer", names)

    def test_pointless_evidence_has_higher_confidence_than_pageview_only(self):
        _index, payloads = build_payloads()
        pms = {answer["name"]: answer for answer in payloads["uk-prime-ministers"]["answers"]}
        countries = {answer["name"]: answer for answer in payloads["countries"]["answers"]}
        self.assertEqual(pms["Henry Pelham"]["obscurity"]["confidence"], "high")
        self.assertEqual(countries["Vanuatu"]["obscurity"]["confidence"], "medium")
        self.assertGreater(len(pms["Henry Pelham"]["obscurity"]["evidence"]), 0)

    def test_user_example_templates_are_exported(self):
        _index, payloads = build_payloads()
        element_template_ids = {
            item["id"] for item in payloads["chemical-elements"]["question_templates"]
        }
        capital_template_ids = {
            item["id"] for item in payloads["us-state-capitals"]["question_templates"]
        }
        self.assertIn("elements-consonant", element_template_ids)
        self.assertIn("state-capitals-containing-state", capital_template_ids)


if __name__ == "__main__":
    unittest.main()
