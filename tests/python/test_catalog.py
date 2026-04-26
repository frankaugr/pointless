import unittest

from pointless_revision.categories import CATEGORIES
from pointless_revision.export import build_payloads


class CatalogTests(unittest.TestCase):
    def test_core_category_pack_is_present(self):
        self.assertGreaterEqual(len(CATEGORIES), 12)
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
            "uk-number-one-singles",
            "uk-number-one-albums",
            "oscar-best-picture-winners",
        ]:
            self.assertIn(slug, CATEGORIES)

    def test_expected_counts_validate(self):
        _index, payloads = build_payloads()
        self.assertEqual(payloads["chemical-elements"]["n_answers"], 118)
        self.assertEqual(payloads["countries"]["n_answers"], 195)
        self.assertEqual(payloads["us-state-capitals"]["n_answers"], 50)
        self.assertEqual(payloads["uk-cities"]["n_answers"], 76)
        self.assertEqual(payloads["uk-number-one-singles"]["n_answers"], 71)
        self.assertEqual(payloads["uk-number-one-albums"]["n_answers"], 83)
        self.assertEqual(payloads["oscar-best-picture-winners"]["n_answers"], 98)

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

    def test_new_revision_packs_have_expected_landmarks(self):
        _index, payloads = build_payloads()
        singles = {answer["name"]: answer for answer in payloads["uk-number-one-singles"]["answers"]}
        albums = {answer["name"]: answer for answer in payloads["uk-number-one-albums"]["answers"]}
        oscars = {answer["name"]: answer for answer in payloads["oscar-best-picture-winners"]["answers"]}
        self.assertEqual(singles["Telstar"]["attrs"]["decade"], "1960s")
        self.assertEqual(albums["Wish You Were Here"]["attrs"]["artist"], "Pink Floyd")
        self.assertEqual(oscars["One Battle After Another"]["attrs"]["year"], 2025)


if __name__ == "__main__":
    unittest.main()
