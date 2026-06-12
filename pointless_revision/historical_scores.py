"""Manual Pointless-score evidence.

This is deliberately small for v1. It establishes the import shape and lets the
exporter weight real show evidence above pageview proxies when it exists.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class HistoricalScore:
    category: str
    answer: str
    score_0_to_100: int
    episode: str
    date: str | None
    question_text: str
    source_url: str
    quote: str | None = None

    def to_json(self) -> dict:
        return asdict(self)


HISTORICAL_SCORES: tuple[HistoricalScore, ...] = (
    HistoricalScore(
        category="uk-prime-ministers",
        answer="Henry Pelham",
        score_0_to_100=0,
        episode="Series 8 Episode 49",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-8/episode-49.html",
    ),
    HistoricalScore(
        category="uk-prime-ministers",
        answer="Thomas Pelham-Holles, 1st Duke of Newcastle",
        score_0_to_100=0,
        episode="Series 8 Episode 49",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-8/episode-49.html",
    ),
    HistoricalScore(
        category="uk-prime-ministers",
        answer="John Russell, 1st Earl Russell",
        score_0_to_100=0,
        episode="Series 8 Episode 49",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-8/episode-49.html",
    ),
    HistoricalScore(
        category="uk-prime-ministers",
        answer="William Lamb, 2nd Viscount Melbourne",
        score_0_to_100=0,
        episode="Series 11 Episode 10",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-11/episode-10.html",
    ),
    HistoricalScore(
        category="uk-prime-ministers",
        answer="Edward Smith-Stanley, 14th Earl of Derby",
        score_0_to_100=0,
        episode="Series 11 Episode 10",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-11/episode-10.html",
    ),
    HistoricalScore(
        category="uk-prime-ministers",
        answer="Archibald Primrose, 5th Earl of Rosebery",
        score_0_to_100=0,
        episode="Series 11 Episode 10",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-11/episode-10.html",
    ),
    HistoricalScore(
        category="uk-prime-ministers",
        answer="Robert Walpole",
        score_0_to_100=1,
        episode="Series 8 Episode 49",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-8/episode-49.html",
    ),
    HistoricalScore(
        category="uk-prime-ministers",
        answer="Winston Churchill",
        score_0_to_100=51,
        episode="Series 8 Episode 49",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-8/episode-49.html",
    ),
    HistoricalScore(
        category="uk-prime-ministers",
        answer="David Cameron",
        score_0_to_100=80,
        episode="Series 11 Episode 10",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-11/episode-10.html",
    ),
    HistoricalScore(
        category="uk-prime-ministers",
        answer="Margaret Thatcher",
        score_0_to_100=82,
        episode="Series 11 Episode 10",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-11/episode-10.html",
    ),
    HistoricalScore(
        category="uk-prime-ministers",
        answer="Tony Blair",
        score_0_to_100=86,
        episode="Series 11 Episode 10",
        date=None,
        question_text="UK prime ministers",
        source_url="https://subsaga.com/bbc/entertainment/pointless/series-11/episode-10.html",
    ),
)


GENERATED_EVIDENCE_PATH = Path(__file__).resolve().parent.parent / "data" / "evidence.json"


def _load_generated(path: Path = GENERATED_EVIDENCE_PATH) -> tuple[HistoricalScore, ...]:
    """Transcript-derived evidence written by `transcripts merge` (optional)."""
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    manual_keys = {(s.category, s.answer, s.episode) for s in HISTORICAL_SCORES}
    records = []
    for row in payload.get("records", []):
        score = HistoricalScore(
            category=row["category"],
            answer=row["answer"],
            score_0_to_100=int(row["score_0_to_100"]),
            episode=row["episode"],
            date=row.get("date"),
            question_text=row.get("question_text", ""),
            source_url=row.get("source_url", ""),
            quote=row.get("evidence_quote") or None,
        )
        if (score.category, score.answer, score.episode) not in manual_keys:
            records.append(score)
    return tuple(records)


GENERATED_SCORES: tuple[HistoricalScore, ...] = _load_generated()


def scores_for(category_slug: str, answer_name: str) -> list[HistoricalScore]:
    return [
        score
        for score in HISTORICAL_SCORES + GENERATED_SCORES
        if score.category == category_slug and score.answer == answer_name
    ]
