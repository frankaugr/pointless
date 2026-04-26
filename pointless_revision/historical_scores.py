"""Manual Pointless-score evidence.

This is deliberately small for v1. It establishes the import shape and lets the
exporter weight real show evidence above pageview proxies when it exists.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HistoricalScore:
    category: str
    answer: str
    score_0_to_100: int
    episode: str
    date: str | None
    question_text: str
    source_url: str

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


def scores_for(category_slug: str, answer_name: str) -> list[HistoricalScore]:
    return [
        score
        for score in HISTORICAL_SCORES
        if score.category == category_slug and score.answer == answer_name
    ]
