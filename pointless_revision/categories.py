"""Category definitions.

Each category is a recurring 'enumerable answer set' that shows up on Pointless
again and again (e.g. UK Prime Ministers, US States, Periodic Table elements).
A category bundles a SPARQL query that returns the canonical answer list, plus
metadata describing how to populate the `answers` table from those results.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    slug: str
    name: str
    description: str
    sparql: str
    name_var: str = "itemLabel"
    qid_uri_var: str = "item"
    article_var: str = "article"


UK_PRIME_MINISTERS = Category(
    slug="uk-prime-ministers",
    name="UK Prime Ministers",
    description=(
        "Every person who has held the office of Prime Minister of the United Kingdom "
        "(Wikidata Q14211). Real humans only — excludes fictional PMs from TV shows."
    ),
    sparql="""
        SELECT DISTINCT ?item ?itemLabel ?article WHERE {
          ?item p:P39/ps:P39 wd:Q14211 .
          ?item wdt:P31 wd:Q5 .
          ?article schema:about ?item ;
                   schema:isPartOf <https://en.wikipedia.org/> .
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
        }
        ORDER BY ?itemLabel
    """,
)


CATEGORIES: dict[str, Category] = {
    UK_PRIME_MINISTERS.slug: UK_PRIME_MINISTERS,
}
