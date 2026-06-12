"""Join the OCR'd final-board card pool with curated question inferences.

`data/final_pool.json` (from scripts/final_pool_report.py) records every
final-round card seen on screen and whether it has been chosen. The cards
never chosen are still in the show's rotation; `data/final_pool_inferences.json`
holds hand-written guesses at the question behind each card plus candidate
pointless answers. This module merges the two into the static payload the
Finals tab reads.
"""

from __future__ import annotations

import json
from pathlib import Path


def build_finals_payload(pool: dict, inferences: dict) -> dict:
    cards = []
    for key, rec in pool.get("cards", {}).items():
        if rec.get("chosen_in"):
            continue
        inference = inferences.get(key, {})
        cards.append(
            {
                "key": key,
                "title": rec.get("title", key),
                "offered": rec.get("offered", []),
                "question": inference.get("question"),
                "picks": inference.get("picks", []),
            }
        )
    cards.sort(key=lambda card: (-len(card["offered"]), card["title"]))
    return {"n_cards": len(cards), "cards": cards}


def write_finals_payload(pool_path: Path, inferences_path: Path, out_path: Path) -> dict:
    pool = json.loads(Path(pool_path).read_text())
    inferences = (
        json.loads(Path(inferences_path).read_text())
        if Path(inferences_path).exists()
        else {}
    )
    payload = build_finals_payload(pool, inferences)
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload
