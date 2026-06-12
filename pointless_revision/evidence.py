"""Merge extracted episode facts into category-keyed score evidence.

Two-stage category resolution: keyword patterns on the extracted category
text first, then answer-overlap voting (a round whose answers mostly match
one curated category is assigned to it). Rounds matching no curated
category are normal — the show covers far more ground than the catalog —
and are reported, not dropped, so they can seed future categories.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from .categories import CATEGORIES
from .export import normalise


CATEGORY_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bus president|president of the (usa|united states)", "us-presidents"),
    (r"prime minister", "uk-prime-ministers"),
    (r"state capital", "us-state-capitals"),
    (r"\b(us|american) state", "us-states"),
    (r"capital cit", "world-capitals"),
    (r"chemical element|periodic table", "chemical-elements"),
    (r"monarch|kings and queens", "english-british-monarchs"),
    (r"best picture|oscar", "oscar-best-picture-winners"),
    (r"number one single|no\.? ?1 single", "uk-number-one-singles"),
    (r"number one album|no\.? ?1 album", "uk-number-one-albums"),
    (r"\b(uk|british) cit", "uk-cities"),
    (r"countr", "countries"),
)

MIN_OVERLAP_FACTS = 2
MIN_OVERLAP_RATIO = 0.6


def is_open_recall(round_data: dict[str, Any]) -> bool:
    """Only canonical "name as many X where Y" rounds feed the app.

    Assisted formats (clue/picture identification, option boards, wordplay)
    measure something other than category recall, so their scores are
    excluded everywhere. Unannotated rounds pass for fixture compatibility.
    """
    return round_data.get("question_format", "open_recall") == "open_recall"


def answer_index() -> dict[str, dict[str, str]]:
    """slug -> normalised name/alias -> canonical answer name."""
    index: dict[str, dict[str, str]] = {}
    for slug, category in CATEGORIES.items():
        lookup: dict[str, str] = {}
        for item in category.answers:
            lookup[normalise(item.name)] = item.name
            for alias in item.aliases:
                lookup.setdefault(normalise(alias), item.name)
        index[slug] = lookup
    return index


def lookup_answer(lookup: dict[str, str], raw: str) -> str | None:
    """Match raw answer text against canonical names/aliases.

    Falls back through parenthetical-stripped and parenthetical-only forms
    ("Czech Republic (Czechia)" matches either part) and a leading "the".
    """
    candidates = [raw]
    no_paren = re.sub(r"\s*\([^)]*\)", "", raw).strip()
    if no_paren and no_paren != raw:
        candidates.append(no_paren)
    candidates.extend(m.group(1) for m in re.finditer(r"\(([^)]+)\)", raw))
    for candidate in candidates:
        norm = normalise(candidate)
        for key in (norm, norm.removeprefix("the ")):
            if key in lookup:
                return lookup[key]
    return None


def resolve_category(round_data: dict[str, Any], index: dict[str, dict[str, str]]) -> str | None:
    category_norm = normalise(round_data.get("category_text", ""))
    for pattern, slug in CATEGORY_PATTERNS:
        if re.search(pattern, category_norm):
            return slug

    answers = [normalise(f["answer"]) for f in round_data.get("facts", []) if f.get("answer")]
    if len(answers) < MIN_OVERLAP_FACTS:
        return None
    votes = Counter()
    for slug, lookup in index.items():
        votes[slug] = sum(1 for a in answers if a in lookup)
    slug, hits = votes.most_common(1)[0]
    if hits >= MIN_OVERLAP_FACTS and hits / len(answers) >= MIN_OVERLAP_RATIO:
        return slug
    return None


def merge_episodes(episodes_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = answer_index()
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    report = {
        "episodes": 0,
        "rounds": 0,
        "rounds_assisted_format": 0,
        "rounds_matched": 0,
        "facts_recorded": 0,
        "facts_skipped_incorrect": 0,
        "facts_skipped_no_score": 0,
        "unmatched_answers": {},
        "unmatched_categories": Counter(),
    }

    for path in sorted(episodes_dir.glob("*.json")):
        episode = json.loads(path.read_text(encoding="utf-8"))
        report["episodes"] += 1
        for round_data in episode.get("rounds", []):
            report["rounds"] += 1
            if not is_open_recall(round_data):
                report["rounds_assisted_format"] += 1
                continue
            slug = resolve_category(round_data, index)
            if slug is None:
                report["unmatched_categories"][round_data.get("category_text", "?")] += 1
                continue
            report["rounds_matched"] += 1
            lookup = index[slug]

            for fact in round_data.get("facts", []):
                if fact.get("is_incorrect"):
                    report["facts_skipped_incorrect"] += 1
                    continue
                score = fact.get("score")
                if score is None and fact.get("is_pointless"):
                    score = 0
                if score is None or not 0 <= int(score) <= 100:
                    report["facts_skipped_no_score"] += 1
                    continue

                canonical = lookup_answer(lookup, fact.get("answer", ""))
                if canonical is None:
                    report["unmatched_answers"].setdefault(slug, []).append(fact["answer"])
                    continue

                key = (slug, canonical, episode["episode_label"])
                if key in seen:
                    continue
                seen.add(key)
                records.append(
                    {
                        "category": slug,
                        "answer": canonical,
                        "score_0_to_100": int(score),
                        "episode": episode["episode_label"],
                        "date": None,
                        "question_text": round_data.get("category_text", ""),
                        "source_url": episode["source_url"],
                        "kind": fact.get("kind", ""),
                        "evidence_quote": (fact.get("evidence_quote") or "")[:160],
                    }
                )
                report["facts_recorded"] += 1

    report["unmatched_categories"] = dict(report["unmatched_categories"].most_common())
    records.sort(key=lambda r: (r["category"], r["answer"], r["episode"]))
    return records, report


MIN_PLAYABLE_FACTS = 4


def build_play_payload(episodes_dir: Path) -> dict[str, Any]:
    """Episode rounds with enough scored facts to play along against.

    Only derived facts ship to the published site: category text, answers,
    and scores. Evidence quotes and full extractions stay in data/.
    """
    episodes = []
    for path in sorted(episodes_dir.glob("*.json")):
        episode = json.loads(path.read_text(encoding="utf-8"))
        rounds = []
        for round_data in episode.get("rounds", []):
            if not is_open_recall(round_data):
                continue
            facts = []
            seen_answers: set[str] = set()
            for fact in round_data.get("facts", []):
                if fact.get("is_incorrect"):
                    continue
                score = fact.get("score")
                if score is None and fact.get("is_pointless"):
                    score = 0
                if score is None or not 0 <= int(score) <= 100:
                    continue
                norm = normalise(fact.get("answer", ""))
                if not norm or norm in seen_answers:
                    continue
                seen_answers.add(norm)
                facts.append(
                    {
                        "answer": fact["answer"],
                        "score": int(score),
                        "is_pointless": bool(fact.get("is_pointless")),
                    }
                )
            if len(facts) >= MIN_PLAYABLE_FACTS:
                rounds.append(
                    {
                        "category_text": round_data.get("category_text", ""),
                        "category_confidence": round_data.get("category_confidence", "low"),
                        "facts": facts,
                    }
                )
        if rounds:
            episodes.append(
                {
                    "episode_id": episode["episode_id"],
                    "episode_label": episode["episode_label"],
                    "source_url": episode["source_url"],
                    "rounds": rounds,
                }
            )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_rounds": sum(len(ep["rounds"]) for ep in episodes),
        "episodes": episodes,
    }


def write_play_payload(episodes_dir: Path, out_path: Path) -> dict[str, Any]:
    payload = build_play_payload(episodes_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def write_evidence(records: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records": records,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
