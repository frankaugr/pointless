"""Populate the SQLite DB with a demo dataset and export JSON for the static site,
without hitting Wikimedia. Useful for CI bootstrapping and offline development.

The pageview values here are coarse hand-graded fame-rank proxies, not real
counts. Run `python scripts/build_data.py` when you have network access to
overwrite this with real Wikidata + pageview data.
"""

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pointless_revision import db, ingest  # noqa: E402

UK_PMS = [
    # (canonical name, wikidata QID, fame-tier 1..5; 1=very famous, 5=very obscure)
    ("Robert Walpole", "Q170067", 2),
    ("Spencer Compton, 1st Earl of Wilmington", "Q353762", 5),
    ("Henry Pelham", "Q333760", 4),
    ("Thomas Pelham-Holles, 1st Duke of Newcastle", "Q333735", 4),
    ("William Cavendish, 4th Duke of Devonshire", "Q433662", 5),
    ("John Stuart, 3rd Earl of Bute", "Q333713", 4),
    ("George Grenville", "Q333778", 4),
    ("Charles Watson-Wentworth, 2nd Marquess of Rockingham", "Q333703", 5),
    ("William Pitt the Elder", "Q170581", 3),
    ("Augustus FitzRoy, 3rd Duke of Grafton", "Q360522", 5),
    ("Frederick North, Lord North", "Q333766", 3),
    ("William Petty, 2nd Earl of Shelburne", "Q333709", 5),
    ("William Cavendish-Bentinck, 3rd Duke of Portland", "Q333753", 5),
    ("William Pitt the Younger", "Q166646", 2),
    ("Henry Addington, 1st Viscount Sidmouth", "Q333774", 5),
    ("William Grenville, 1st Baron Grenville", "Q333783", 5),
    ("Spencer Perceval", "Q132805", 4),
    ("Robert Jenkinson, 2nd Earl of Liverpool", "Q333748", 4),
    ("George Canning", "Q170587", 4),
    ("Frederick Robinson, 1st Viscount Goderich", "Q333769", 5),
    ("Arthur Wellesley, 1st Duke of Wellington", "Q131691", 1),
    ("Charles Grey, 2nd Earl Grey", "Q170066", 4),
    ("William Lamb, 2nd Viscount Melbourne", "Q333787", 4),
    ("Robert Peel", "Q170581_peel", 2),
    ("John Russell, 1st Earl Russell", "Q333744", 4),
    ("Edward Smith-Stanley, 14th Earl of Derby", "Q333725", 4),
    ("George Hamilton-Gordon, 4th Earl of Aberdeen", "Q333730", 4),
    ("Henry John Temple, 3rd Viscount Palmerston", "Q170587_p", 3),
    ("Benjamin Disraeli", "Q172832", 1),
    ("William Ewart Gladstone", "Q44226", 1),
    ("Robert Gascoyne-Cecil, 3rd Marquess of Salisbury", "Q166233", 3),
    ("Archibald Primrose, 5th Earl of Rosebery", "Q156110", 5),
    ("Arthur Balfour", "Q156268", 3),
    ("Henry Campbell-Bannerman", "Q156142", 4),
    ("H. H. Asquith", "Q133764", 3),
    ("David Lloyd George", "Q132805_llg", 2),
    ("Bonar Law", "Q333713_bl", 4),
    ("Stanley Baldwin", "Q333737", 3),
    ("Ramsay MacDonald", "Q156347", 3),
    ("Neville Chamberlain", "Q132764", 3),
    ("Winston Churchill", "Q8016", 1),
    ("Clement Attlee", "Q166663", 2),
    ("Anthony Eden", "Q156268_ae", 3),
    ("Harold Macmillan", "Q156412", 2),
    ("Alec Douglas-Home", "Q333713_adh", 5),
    ("Harold Wilson", "Q166689", 2),
    ("Edward Heath", "Q165421", 2),
    ("James Callaghan", "Q165824", 2),
    ("Margaret Thatcher", "Q7416", 1),
    ("John Major", "Q165792", 2),
    ("Tony Blair", "Q9582", 1),
    ("Gordon Brown", "Q132805_gb", 2),
    ("David Cameron", "Q192", 1),
    ("Theresa May", "Q264766", 2),
    ("Boris Johnson", "Q180589", 1),
    ("Liz Truss", "Q22308", 2),
    ("Rishi Sunak", "Q22059256", 2),
    ("Keir Starmer", "Q282636", 1),
]


def article_from_name(name: str) -> str:
    return "https://en.wikipedia.org/wiki/" + name.replace(" ", "_")


def fame_to_pageviews(tier: int) -> int:
    return {1: 5_000_000, 2: 1_500_000, 3: 400_000, 4: 100_000, 5: 25_000}[tier]


def main() -> int:
    db.init_schema()

    fake_sparql_rows = [
        {
            "item": f"http://www.wikidata.org/entity/{qid}",
            "itemLabel": name,
            "article": article_from_name(name),
        }
        for (name, qid, _tier) in UK_PMS
    ]
    fake_pageviews = {
        article_from_name(name).rsplit("/", 1)[-1]: fame_to_pageviews(tier)
        for (name, _qid, tier) in UK_PMS
    }

    with patch("pointless_revision.ingest.run_sparql", return_value=fake_sparql_rows):
        cat_id, n = ingest.fetch_category_answers("uk-prime-ministers")
    print(f"seeded {n} answers (cat_id={cat_id})")

    with patch("pointless_revision.ingest.fetch_pageviews_polite", return_value=fake_pageviews):
        n = ingest.fetch_pageviews_for_category("uk-prime-ministers")
    print(f"seeded pageviews for {n} answers")

    n = ingest.recompute_obscurity("uk-prime-ministers")
    print(f"scored {n} answers")

    from build_data import main as build_main
    return build_main(["--skip-fetch"])


if __name__ == "__main__":
    sys.exit(main())
