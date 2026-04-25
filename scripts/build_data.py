"""Run the ingest pipeline for every registered category and export JSON
files into docs/data/ for the static site to consume.

Usage:
    python scripts/build_data.py [--months 12]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pointless_revision import db, ingest  # noqa: E402
from pointless_revision.categories import CATEGORIES  # noqa: E402


DOCS_DATA = ROOT / "docs" / "data"


def export_category(slug: str) -> dict:
    with db.connect() as conn:
        cat = conn.execute(
            "SELECT id, slug, name, description, fetched_at FROM categories WHERE slug = ?",
            (slug,),
        ).fetchone()
        if cat is None:
            raise SystemExit(f"category {slug!r} not in DB")

        rows = conn.execute(
            """
            SELECT a.canonical_name, a.wikidata_qid, a.wiki_article,
                   sig.value_num AS pageviews,
                   sc.score      AS obscurity
            FROM answers a
            LEFT JOIN obscurity_signals sig
              ON sig.answer_id = a.id AND sig.signal_type = 'wikipedia_pageviews'
            LEFT JOIN obscurity_scores sc ON sc.answer_id = a.id
            WHERE a.category_id = ?
            ORDER BY COALESCE(sc.score, 0) DESC, a.canonical_name
            """,
            (cat["id"],),
        ).fetchall()

    answers = [
        {
            "name": r["canonical_name"],
            "qid": r["wikidata_qid"],
            "wiki": r["wiki_article"],
            "pageviews": int(r["pageviews"]) if r["pageviews"] is not None else None,
            "obscurity": round(r["obscurity"], 4) if r["obscurity"] is not None else None,
        }
        for r in rows
    ]

    return {
        "slug": cat["slug"],
        "name": cat["name"],
        "description": cat["description"],
        "fetched_at": cat["fetched_at"],
        "n_answers": len(answers),
        "answers": answers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=12, help="Months of pageview history")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip Wikidata + pageviews; just re-export from existing DB")
    args = parser.parse_args(argv)

    db.init_schema()
    DOCS_DATA.mkdir(parents=True, exist_ok=True)

    index = []
    for slug in CATEGORIES:
        if not args.skip_fetch:
            print(f"[{slug}] fetching answers from Wikidata...")
            ingest.fetch_category_answers(slug)
            print(f"[{slug}] fetching Wikipedia pageviews...")
            ingest.fetch_pageviews_for_category(slug, months_back=args.months)
            print(f"[{slug}] computing obscurity scores...")
            ingest.recompute_obscurity(slug)

        payload = export_category(slug)
        out_path = DOCS_DATA / f"{slug}.json"
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"[{slug}] wrote {payload['n_answers']} answers -> {out_path.relative_to(ROOT)}")

        index.append(
            {
                "slug": payload["slug"],
                "name": payload["name"],
                "description": payload["description"],
                "n_answers": payload["n_answers"],
            }
        )

    (DOCS_DATA / "categories.json").write_text(
        json.dumps(
            {"generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z", "categories": index},
            indent=2,
        )
    )
    print(f"wrote categories index ({len(index)} categories)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
