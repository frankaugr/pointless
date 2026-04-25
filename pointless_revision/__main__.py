import argparse
import sys

from .categories import CATEGORIES
from .db import init_schema
from .ingest import fetch_category_answers, fetch_pageviews_for_category, recompute_obscurity
from .db import connect


def cmd_init(_args) -> int:
    init_schema()
    print("Schema initialised.")
    return 0


def cmd_categories(_args) -> int:
    for slug, cat in CATEGORIES.items():
        print(f"{slug:30s}  {cat.name}")
    return 0


def cmd_fetch(args) -> int:
    init_schema()
    cat_id, n = fetch_category_answers(args.category)
    print(f"Loaded {n} answers into category id={cat_id} ({args.category}).")
    return 0


def cmd_pageviews(args) -> int:
    n = fetch_pageviews_for_category(args.category, months_back=args.months)
    print(f"Captured pageviews for {n} answers in {args.category}.")
    return 0


def cmd_score(args) -> int:
    n = recompute_obscurity(args.category)
    print(f"Recomputed obscurity scores for {n} answers in {args.category}.")
    return 0


def cmd_show(args) -> int:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT a.canonical_name, a.wikidata_qid,
                   sig.value_num AS pageviews,
                   sc.score      AS obscurity
            FROM answers a
            JOIN categories c ON c.id = a.category_id
            LEFT JOIN obscurity_signals sig
              ON sig.answer_id = a.id AND sig.signal_type = 'wikipedia_pageviews'
            LEFT JOIN obscurity_scores sc ON sc.answer_id = a.id
            WHERE c.slug = ?
            ORDER BY COALESCE(sc.score, 0) DESC
            LIMIT ?
            """,
            (args.category, args.limit),
        ).fetchall()

    if not rows:
        print(f"No data for {args.category}. Run `fetch` first.")
        return 1

    print(f"{'name':40s}  {'qid':12s}  {'pageviews':>10s}  {'obscurity':>9s}")
    print("-" * 80)
    for r in rows:
        pv = f"{int(r['pageviews']):,}" if r["pageviews"] is not None else "-"
        sc = f"{r['obscurity']:.3f}" if r["obscurity"] is not None else "-"
        print(f"{r['canonical_name']:40s}  {r['wikidata_qid'] or '-':12s}  {pv:>10s}  {sc:>9s}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pointless_revision")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create the SQLite schema").set_defaults(func=cmd_init)
    sub.add_parser("categories", help="List known categories").set_defaults(func=cmd_categories)

    p_fetch = sub.add_parser("fetch", help="Fetch a category's answers from Wikidata")
    p_fetch.add_argument("category")
    p_fetch.set_defaults(func=cmd_fetch)

    p_pv = sub.add_parser("pageviews", help="Fetch Wikipedia pageviews for a category")
    p_pv.add_argument("category")
    p_pv.add_argument("--months", type=int, default=12)
    p_pv.set_defaults(func=cmd_pageviews)

    p_score = sub.add_parser("score", help="Recompute obscurity scores for a category")
    p_score.add_argument("category")
    p_score.set_defaults(func=cmd_score)

    p_show = sub.add_parser("show", help="Show answers ranked by obscurity")
    p_show.add_argument("category")
    p_show.add_argument("--limit", type=int, default=200)
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
