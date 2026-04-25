import json
import math
from datetime import datetime

from .categories import Category, CATEGORIES
from .db import connect
from .pageviews import article_slug_from_url, fetch_pageviews_polite
from .wikidata import qid_from_uri, run_sparql


def upsert_category(conn, category: Category) -> int:
    conn.execute(
        """
        INSERT INTO categories (slug, name, description, source_kind, source_query, fetched_at)
        VALUES (?, ?, ?, 'wikidata-sparql', ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
          name = excluded.name,
          description = excluded.description,
          source_query = excluded.source_query,
          fetched_at = excluded.fetched_at
        """,
        (
            category.slug,
            category.name,
            category.description,
            category.sparql,
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )
    row = conn.execute("SELECT id FROM categories WHERE slug = ?", (category.slug,)).fetchone()
    return row["id"]


def fetch_category_answers(category_slug: str) -> tuple[int, int]:
    """Run the category's SPARQL and upsert into the answers table.

    Returns (category_id, num_answers).
    """
    category = CATEGORIES[category_slug]
    rows = run_sparql(category.sparql)

    with connect() as conn:
        category_id = upsert_category(conn, category)

        for row in rows:
            name = row.get(category.name_var)
            if not name:
                continue
            qid = qid_from_uri(row.get(category.qid_uri_var, ""))
            article = row.get(category.article_var)
            extra = {k: v for k, v in row.items() if k not in {category.name_var, category.qid_uri_var, category.article_var}}

            conn.execute(
                """
                INSERT INTO answers (category_id, canonical_name, wikidata_qid, wiki_article, extra_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(category_id, canonical_name) DO UPDATE SET
                  wikidata_qid = excluded.wikidata_qid,
                  wiki_article = excluded.wiki_article,
                  extra_json   = excluded.extra_json
                """,
                (category_id, name, qid, article, json.dumps(extra) if extra else None),
            )

        n = conn.execute(
            "SELECT COUNT(*) AS n FROM answers WHERE category_id = ?", (category_id,)
        ).fetchone()["n"]

    return category_id, n


def fetch_pageviews_for_category(category_slug: str, months_back: int = 12) -> int:
    """Fetch Wikipedia pageviews for every answer in a category and store as a signal."""
    with connect() as conn:
        cat = conn.execute("SELECT id FROM categories WHERE slug = ?", (category_slug,)).fetchone()
        if cat is None:
            raise ValueError(f"Unknown category: {category_slug}")
        rows = conn.execute(
            "SELECT id, canonical_name, wiki_article FROM answers WHERE category_id = ? AND wiki_article IS NOT NULL",
            (cat["id"],),
        ).fetchall()

    article_to_answer = {}
    for r in rows:
        slug = article_slug_from_url(r["wiki_article"])
        if slug:
            article_to_answer[slug] = r["id"]

    pageviews = fetch_pageviews_polite(list(article_to_answer.keys()), months_back=months_back)

    with connect() as conn:
        for slug, views in pageviews.items():
            answer_id = article_to_answer[slug]
            conn.execute(
                """
                INSERT INTO obscurity_signals (answer_id, signal_type, value_num, source)
                VALUES (?, 'wikipedia_pageviews', ?, ?)
                ON CONFLICT(answer_id, signal_type, source) DO UPDATE SET
                  value_num = excluded.value_num,
                  captured_at = datetime('now')
                """,
                (answer_id, float(views), f"en.wikipedia/last_{months_back}_months"),
            )
    return len(pageviews)


def recompute_obscurity(category_slug: str) -> int:
    """Compute a 0..1 obscurity score per answer in a category from current signals.

    For now: 1 - normalised(log(pageviews + 1)) within the category.
    Higher score = more obscure = better Pointless candidate.
    """
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT a.id AS answer_id, COALESCE(s.value_num, 0) AS pv
            FROM answers a
            JOIN categories c ON c.id = a.category_id
            LEFT JOIN obscurity_signals s
              ON s.answer_id = a.id AND s.signal_type = 'wikipedia_pageviews'
            WHERE c.slug = ?
            """,
            (category_slug,),
        ).fetchall()

        if not rows:
            return 0

        log_pvs = [math.log(r["pv"] + 1) for r in rows]
        lo, hi = min(log_pvs), max(log_pvs)
        span = hi - lo if hi > lo else 1.0

        for r, lp in zip(rows, log_pvs):
            normalised_fame = (lp - lo) / span
            score = 1.0 - normalised_fame
            components = {"log_pageviews": lp, "normalised_fame": normalised_fame}
            conn.execute(
                """
                INSERT INTO obscurity_scores (answer_id, score, components_json, computed_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(answer_id) DO UPDATE SET
                  score = excluded.score,
                  components_json = excluded.components_json,
                  computed_at = excluded.computed_at
                """,
                (r["answer_id"], score, json.dumps(components)),
            )

    return len(rows)
