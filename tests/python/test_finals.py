import json
import tempfile
import unittest
from pathlib import Path

from pointless_revision.finals import build_finals_payload, write_finals_payload


def pool(cards):
    return {"cards": cards}


class FinalsPayloadTests(unittest.TestCase):
    def test_only_unchosen_cards_are_included(self):
        payload = build_finals_payload(
            pool({
                "EGGS": {"title": "Eggs", "offered": ["s34e02", "s34e15"], "chosen_in": "s34e15"},
                "ANDYMURRAY": {"title": "Andy Murray", "offered": ["s34e29"], "chosen_in": None},
            }),
            {},
        )
        self.assertEqual(payload["n_cards"], 1)
        self.assertEqual(payload["cards"][0]["key"], "ANDYMURRAY")

    def test_sorted_by_offer_count_then_title(self):
        payload = build_finals_payload(
            pool({
                "B": {"title": "Bravo", "offered": ["s34e01"], "chosen_in": None},
                "A": {"title": "Alpha", "offered": ["s34e01"], "chosen_in": None},
                "C": {"title": "Charlie", "offered": ["s34e01", "s34e02"], "chosen_in": None},
            }),
            {},
        )
        self.assertEqual([c["title"] for c in payload["cards"]], ["Charlie", "Alpha", "Bravo"])

    def test_inference_join_and_missing_inference(self):
        payload = build_finals_payload(
            pool({
                "ANDYMURRAY": {"title": "Andy Murray", "offered": ["s34e29"], "chosen_in": None},
                "WINE": {"title": "Wine", "offered": ["s35e09"], "chosen_in": None},
            }),
            {
                "ANDYMURRAY": {
                    "question": "Name any tournament Murray won.",
                    "picks": [{"answer": "San Jose", "note": "first title"}],
                }
            },
        )
        by_key = {c["key"]: c for c in payload["cards"]}
        self.assertEqual(by_key["ANDYMURRAY"]["question"], "Name any tournament Murray won.")
        self.assertEqual(by_key["ANDYMURRAY"]["picks"][0]["answer"], "San Jose")
        self.assertIsNone(by_key["WINE"]["question"])
        self.assertEqual(by_key["WINE"]["picks"], [])

    def test_write_payload_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "pool.json").write_text(json.dumps(pool({
                "WINE": {"title": "Wine", "offered": ["s35e09"], "chosen_in": None},
            })))
            out = tmp / "finals.json"
            payload = write_finals_payload(tmp / "pool.json", tmp / "missing.json", out)
            self.assertEqual(payload["n_cards"], 1)
            self.assertEqual(json.loads(out.read_text()), payload)


if __name__ == "__main__":
    unittest.main()
