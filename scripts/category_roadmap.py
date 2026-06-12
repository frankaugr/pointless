"""Mine unmatched episode rounds for recurring category families.

Rounds that don't map to a curated category are the backlog for new ones.
This groups their category texts by topic keyword so the most recurrent
families float to the top, and writes data/category_roadmap.md.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pointless_revision.evidence import answer_index, is_open_recall, resolve_category  # noqa: E402


# Question-mechanic vocabulary that says nothing about the topic.
MECHANIC_WORDS = {
    "a", "an", "and", "any", "anyone", "are", "as", "at", "based", "beginning", "between",
    "board", "but", "by", "can", "clue", "clues", "containing", "correct", "definitions",
    "described", "descriptions", "drawings", "each", "ending", "etc", "famous", "fill",
    "find", "first", "five", "followed", "four", "from", "gaps", "given", "had", "has",
    "have", "her", "his", "identify", "in", "initial", "initials", "is", "it", "its",
    "jackpot", "last", "letter", "letters", "list", "made", "missing", "more", "most",
    "name", "named", "names", "not", "of", "on", "one", "ones", "or", "order", "other",
    "our", "out", "part", "people", "person", "pictures", "pointless", "real", "see",
    "seven", "shown", "six", "some", "than", "that", "the", "their", "these", "they",
    "this", "three", "titles", "to", "two", "up", "used", "was", "we", "well", "were",
    "what", "when", "where", "which", "who", "whose", "with", "word", "words", "you",
    "alphabetical", "alternate", "anagram", "anagrams", "blanks", "vowels",
}


def tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9']+", text.lower())
        if len(token) >= 3 and token not in MECHANIC_WORDS
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=Path, default=ROOT / "data" / "episodes")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "category_roadmap.md")
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args(argv)

    index = answer_index()
    unmatched: list[tuple[str, str]] = []
    for path in sorted(args.episodes.glob("*.json")):
        episode = json.loads(path.read_text(encoding="utf-8"))
        for round_data in episode.get("rounds", []):
            if not is_open_recall(round_data):
                continue
            if resolve_category(round_data, index) is None:
                unmatched.append((episode["episode_label"], round_data.get("category_text", "")))

    by_keyword: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for episode_label, category_text in unmatched:
        for token in set(tokens(category_text)):
            by_keyword[token].append((episode_label, category_text))

    ranked = sorted(by_keyword.items(), key=lambda kv: (-len(kv[1]), kv[0]))[: args.top]

    lines = [
        "# Category roadmap",
        "",
        f"{len(unmatched)} open-recall rounds do not map to any curated category.",
        "Recurring topic keywords below suggest which new categories would pay off",
        "fastest; each new curated category immediately attaches its real show",
        "scores via `transcripts merge`.",
        "",
        "| Keyword | Rounds | Examples |",
        "| --- | --- | --- |",
    ]
    for keyword, rounds in ranked:
        examples = "<br>".join(
            f"{label}: {text[:90]}" for label, text in rounds[:3]
        )
        lines.append(f"| {keyword} | {len(rounds)} | {examples} |")

    lines += ["", "## All unmatched rounds", ""]
    lines += [f"- {label}: {text}" for label, text in sorted(unmatched)]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(unmatched)} unmatched rounds -> {args.out.relative_to(ROOT)}")
    print("top keywords:", ", ".join(f"{k} ({len(v)})" for k, v in ranked[:10]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
