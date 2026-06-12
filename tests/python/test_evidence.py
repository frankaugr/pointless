import json
import tempfile
import unittest
from pathlib import Path

from pointless_revision.evidence import (
    answer_index,
    build_play_payload,
    lookup_answer,
    merge_episodes,
    resolve_category,
)
from pointless_revision.historical_scores import _load_generated


def episode_payload(rounds):
    return {
        "episode_id": "s34e01",
        "episode_label": "Series 34 Episode 1",
        "series": 34,
        "episode": 1,
        "pid": "m002jwx4",
        "source_url": "https://www.bbc.co.uk/programmes/m002jwx4",
        "rounds": rounds,
    }


def fact(answer, score=None, kind="guess", is_pointless=False, is_incorrect=False):
    return {
        "answer": answer,
        "score": score,
        "is_pointless": is_pointless,
        "is_incorrect": is_incorrect,
        "kind": kind,
        "contestant": None,
        "evidence_quote": "quote",
    }


class CategoryResolutionTests(unittest.TestCase):
    def setUp(self):
        self.index = answer_index()

    def test_keyword_match(self):
        round_data = {"category_text": "UK Prime Ministers", "facts": []}
        self.assertEqual(resolve_category(round_data, self.index), "uk-prime-ministers")

    def test_answer_overlap_vote(self):
        round_data = {
            "category_text": "Teams in Euro 2024",
            "facts": [fact("Italy"), fact("Portugal"), fact("Czech Republic")],
        }
        # All three are countries; overlap voting should assign the round.
        self.assertEqual(resolve_category(round_data, self.index), "countries")

    def test_lookup_answer_fallbacks(self):
        countries = self.index["countries"]
        self.assertEqual(lookup_answer(countries, "The Netherlands"), "Netherlands")
        self.assertEqual(lookup_answer(countries, "Czech Republic (Czechia)"), "Czechia")
        self.assertEqual(lookup_answer(countries, "Czechia (Czech Republic)"), "Czechia")
        self.assertIsNone(lookup_answer(countries, "Manitoba Moose"))

    def test_no_match_returns_none(self):
        round_data = {
            "category_text": "Films featuring talking dogs",
            "facts": [fact("Beethoven"), fact("Marmaduke"), fact("Scooby-Doo")],
        }
        self.assertIsNone(resolve_category(round_data, self.index))


class MergeTests(unittest.TestCase):
    def merge(self, rounds):
        with tempfile.TemporaryDirectory() as tmp:
            episodes_dir = Path(tmp)
            (episodes_dir / "s34e01.json").write_text(
                json.dumps(episode_payload(rounds)), encoding="utf-8"
            )
            return merge_episodes(episodes_dir)

    def test_alias_resolves_to_canonical_name(self):
        records, report = self.merge(
            [
                {
                    "category_text": "Countries that competed at Euro 2024",
                    "category_confidence": "high",
                    "facts": [
                        fact("Italy", score=57),
                        fact("Czech Republic", score=3, kind="recap_lowest"),
                    ],
                }
            ]
        )
        self.assertEqual(report["facts_recorded"], 2)
        czech = next(r for r in records if r["score_0_to_100"] == 3)
        self.assertEqual(czech["answer"], "Czechia")
        self.assertEqual(czech["category"], "countries")
        self.assertEqual(czech["episode"], "Series 34 Episode 1")

    def test_pointless_without_stated_score_becomes_zero(self):
        records, _report = self.merge(
            [
                {
                    "category_text": "UK prime ministers",
                    "category_confidence": "high",
                    "facts": [fact("Robert Walpole", is_pointless=True, kind="recap_pointless")],
                }
            ]
        )
        self.assertEqual(records[0]["score_0_to_100"], 0)

    def test_incorrect_and_unscored_facts_are_skipped(self):
        records, report = self.merge(
            [
                {
                    "category_text": "UK prime ministers",
                    "category_confidence": "high",
                    "facts": [
                        fact("Winston Churchill", score=51, is_incorrect=True),
                        fact("Robert Walpole"),
                    ],
                }
            ]
        )
        self.assertEqual(records, [])
        self.assertEqual(report["facts_skipped_incorrect"], 1)
        self.assertEqual(report["facts_skipped_no_score"], 1)

    def test_play_payload_keeps_only_scoreable_rounds(self):
        rounds = [
            {
                "category_text": "Teams at Euro 2024",
                "category_confidence": "high",
                "facts": [
                    fact("Italy", score=57),
                    fact("Italy", score=57),  # duplicate answer -> dropped
                    fact("Czechia", score=3),
                    fact("Georgia", is_pointless=True),  # null score -> 0
                    fact("Slovakia", score=100, is_incorrect=True),  # excluded
                    fact("Poland", score=16),
                ],
            },
            {
                "category_text": "Too thin",
                "category_confidence": "low",
                "facts": [fact("One", score=1), fact("Two", score=2)],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            episodes_dir = Path(tmp)
            (episodes_dir / "s34e01.json").write_text(
                json.dumps(episode_payload(rounds)), encoding="utf-8"
            )
            payload = build_play_payload(episodes_dir)
        self.assertEqual(payload["n_rounds"], 1)
        facts = payload["episodes"][0]["rounds"][0]["facts"]
        self.assertEqual(len(facts), 4)
        georgia = next(f for f in facts if f["answer"] == "Georgia")
        self.assertEqual(georgia["score"], 0)
        self.assertTrue(georgia["is_pointless"])

    def test_generated_evidence_loader_skips_manual_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.json"
            path.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "category": "countries",
                                "answer": "Czechia",
                                "score_0_to_100": 3,
                                "episode": "Series 34 Episode 1",
                                "question_text": "Euro 2024 teams",
                                "source_url": "https://www.bbc.co.uk/programmes/m002jwx4",
                            },
                            # Duplicates a manual HISTORICAL_SCORES row -> dropped.
                            {
                                "category": "uk-prime-ministers",
                                "answer": "Henry Pelham",
                                "score_0_to_100": 0,
                                "episode": "Series 8 Episode 49",
                                "question_text": "UK prime ministers",
                                "source_url": "https://example.com",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            loaded = _load_generated(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].answer, "Czechia")


if __name__ == "__main__":
    unittest.main()
