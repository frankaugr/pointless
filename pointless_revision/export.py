"""Export curated category specs into static JSON payloads."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

from .categories import AnswerSpec, CATEGORIES, CategorySpec, slugify
from .historical_scores import scores_for


VOWELS = set("aeiou")


def normalise(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def derived_attrs(answer: AnswerSpec) -> dict[str, Any]:
    name_norm = normalise(answer.name)
    compact = name_norm.replace(" ", "")
    first = compact[:1]
    first_vowel = next((ch for ch in compact if ch in VOWELS), "")
    attrs = dict(answer.attrs)
    attrs.update(
        {
            "name_initial": first.upper(),
            "name_length": len(compact),
            "starts_with_vowel": first in VOWELS,
            "starts_with_consonant": bool(first and first not in VOWELS and first.isalpha()),
            "first_vowel": first_vowel,
        }
    )
    return attrs


def pageview_proxy(answer: AnswerSpec, category: CategorySpec) -> int:
    if answer.pageviews is not None:
        return answer.pageviews
    digest = hashlib.sha1(f"{category.slug}:{answer.name}".encode("utf-8")).hexdigest()
    jitter = int(digest[:6], 16) % 25_000
    fame = max(1, min(10, answer.fame))
    return int(18_000 + (fame**2.35 * 28_000) + jitter)


def _percentiles(values: list[float]) -> list[float]:
    if len(values) == 1:
        return [0.5]
    order = sorted(range(len(values)), key=lambda i: values[i])
    pct = [0.0] * len(values)
    for rank, original_index in enumerate(order):
        pct[original_index] = rank / (len(values) - 1)
    return pct


def _band(score: float) -> str:
    if score >= 0.82:
        return "pointless target"
    if score >= 0.66:
        return "very obscure"
    if score >= 0.45:
        return "useful low scorer"
    if score >= 0.25:
        return "middling"
    return "obvious"


def _pointless_band(pointless_score: int) -> str:
    if pointless_score == 0:
        return "pointless target"
    if pointless_score <= 10:
        return "excellent"
    if pointless_score <= 30:
        return "strong low scorer"
    if pointless_score <= 50:
        return "playable"
    return "high scorer"


def _score_answer(answer: AnswerSpec, category: CategorySpec, pageviews: int, pageview_percentile: float) -> dict[str, Any]:
    pv_obscurity = 1.0 - pageview_percentile
    score_evidence = scores_for(category.slug, answer.name)
    components: dict[str, Any] = {
        "pageviews": pageviews,
        "pageview_source": "curated_pageview_proxy" if answer.pageviews is None else "wikipedia_pageviews",
        "pageview_obscurity": round(pv_obscurity, 4),
    }

    average_score = None
    if score_evidence:
        average_score = sum(score.score_0_to_100 for score in score_evidence) / len(score_evidence)
        pointless_obscurity = 1.0 - (average_score / 100.0)
        score = (pointless_obscurity * 0.75) + (pv_obscurity * 0.25)
        components.update(
            {
                "pointless_average_score": round(average_score, 2),
                "pointless_obscurity": round(pointless_obscurity, 4),
                "pointless_observations": len(score_evidence),
            }
        )
        confidence = "high"
    else:
        score = pv_obscurity
        confidence = "medium"

    score = max(0.0, min(1.0, score))
    pointless_score = round(average_score) if average_score is not None else round((1.0 - score) * 100)
    pointless_score = max(0, min(100, pointless_score))
    return {
        "score": round(score, 4),
        "band": _band(score),
        "pointless_score": pointless_score,
        "pointless_band": _pointless_band(pointless_score),
        "confidence": confidence,
        "components": components,
        "evidence": [item.to_json() for item in score_evidence],
    }


def category_payload(category: CategorySpec) -> dict[str, Any]:
    ids = [answer.id or slugify(answer.name) for answer in category.answers]
    duplicate_ids = [item for item, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        raise ValueError(f"{category.slug} has duplicate answer ids: {duplicate_ids}")
    if len(category.answers) != category.expected_count:
        raise ValueError(
            f"{category.slug} expected {category.expected_count} answers, got {len(category.answers)}"
        )

    pageviews = [pageview_proxy(answer, category) for answer in category.answers]
    log_pageviews = [math.log(value + 1) for value in pageviews]
    pageview_percentiles = _percentiles(log_pageviews)

    answers = []
    for idx, answer in enumerate(category.answers):
        attrs = derived_attrs(answer)
        answers.append(
            {
                "id": ids[idx],
                "name": answer.name,
                "aliases": list(answer.aliases),
                "qid": answer.qid,
                "wiki": answer.wiki,
                "attrs": attrs,
                "pageviews": pageviews[idx],
                "obscurity": _score_answer(answer, category, pageviews[idx], pageview_percentiles[idx]),
            }
        )

    answers.sort(key=lambda item: (-item["obscurity"]["score"], item["name"]))
    return {
        "slug": category.slug,
        "name": category.name,
        "description": category.description,
        "tags": list(category.tags),
        "answer_kind": category.answer_kind,
        "expected_count": category.expected_count,
        "n_answers": len(answers),
        "display_fields": list(category.display_fields),
        "question_templates": list(category.question_templates),
        "sources": list(category.sources),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "answers": answers,
    }


def build_payloads() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    category_payloads = {slug: category_payload(category) for slug, category in CATEGORIES.items()}
    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "categories": [
            {
                "slug": payload["slug"],
                "name": payload["name"],
                "description": payload["description"],
                "tags": payload["tags"],
                "answer_kind": payload["answer_kind"],
                "n_answers": payload["n_answers"],
                "display_fields": payload["display_fields"],
            }
            for payload in category_payloads.values()
        ],
    }
    return index, category_payloads


def write_static_data(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    index, category_payloads = build_payloads()
    for slug, payload in category_payloads.items():
        (out_dir / f"{slug}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    (out_dir / "categories.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
