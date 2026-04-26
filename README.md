# Pointless Revision

A static revision tool for recurring Pointless-style answer sets. The app has two modes:

- Learn: browse finite categories, sort by obscurity, hide/reveal answers, and mark answers as known or needing work.
- Revise: answer generated narrowed prompts such as chemical elements by name pattern, countries by continent, or US state capitals containing selected letters.

## Data Model

The canonical v1 answer sets live in `pointless_revision/categories.py`. They are curated fixtures, not live Wikidata queries. The exporter enriches each answer with:

- aliases and category-specific attributes
- a pageview-style obscurity proxy
- optional manually sourced historical Pointless scores from `pointless_revision/historical_scores.py`

Historical score rows use this shape: `category`, `answer`, `score_0_to_100`, `episode`, `date`, `question_text`, and `source_url`.

## Build And Test

```sh
python3 scripts/build_data.py
python3 -m pointless_revision validate
python3 -m unittest discover -s tests/python
node --test tests/js/*.test.mjs
```

For local viewing:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 -d docs
```

Then open `http://127.0.0.1:8765/`.
