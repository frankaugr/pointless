import time
from datetime import date, timedelta
from urllib.parse import quote

import requests

PAGEVIEWS_BASE = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "en.wikipedia/all-access/all-agents/{article}/monthly/{start}/{end}"
)
USER_AGENT = "pointless-revision/0.1 (https://github.com/frankaugr/pointless; personal study tool)"


def article_slug_from_url(wiki_url: str) -> str | None:
    if not wiki_url:
        return None
    return wiki_url.rsplit("/", 1)[-1]


def monthly_pageviews(article: str, months_back: int = 12) -> int:
    """Total pageviews for an English-Wikipedia article over the last `months_back` months."""
    end = date.today().replace(day=1) - timedelta(days=1)
    start_year = end.year - (months_back // 12)
    start_month = end.month - (months_back % 12)
    if start_month <= 0:
        start_month += 12
        start_year -= 1
    start = date(start_year, start_month, 1)

    url = PAGEVIEWS_BASE.format(
        article=quote(article, safe=""),
        start=start.strftime("%Y%m%d"),
        end=end.strftime("%Y%m%d"),
    )
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    if resp.status_code == 404:
        return 0
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return sum(int(item.get("views", 0)) for item in items)


def fetch_pageviews_polite(articles: list[str], months_back: int = 12, sleep_s: float = 0.1) -> dict[str, int]:
    out: dict[str, int] = {}
    for art in articles:
        if art is None:
            continue
        out[art] = monthly_pageviews(art, months_back=months_back)
        time.sleep(sleep_s)
    return out
