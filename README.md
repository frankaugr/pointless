# Pointless Revision

A static revision tool for recurring Pointless-style answer sets. The app has three modes:

- Learn: browse finite categories, sort by obscurity, hide/reveal answers, and mark answers as known or needing work. Answers seen on the show carry an expandable evidence panel (score, episode, question, quote).
- Revise: answer generated narrowed prompts such as chemical elements by name pattern, countries by continent, or US state capitals containing selected letters.
- Play: real rounds from series 34-35 — give answers against the actual category, then compare with what the surveyed 100 said. Boards are limited to answers spoken aloud in each episode.

## Data Model

The canonical v1 answer sets live in `pointless_revision/categories.py`. They are curated fixtures, not live Wikidata queries. The exporter enriches each answer with:

- aliases and category-specific attributes
- a pageview-style obscurity proxy
- optional manually sourced historical Pointless scores from `pointless_revision/historical_scores.py`

Historical score rows use this shape: `category`, `answer`, `score_0_to_100`, `episode`, `date`, `question_text`, and `source_url`.

## Transcript Evidence Pipeline

Subtitle transcripts (`pointless_transcripts/sNN/*.srt`, untracked) can be turned into real show evidence that the exporter weights above the pageview proxy:

```sh
.venv/bin/pip install anthropic            # one-time
export ANTHROPIC_API_KEY=...

# Extract one episode (prompt iteration) or the full corpus (Batch API, 50% cheaper):
.venv/bin/python -m pointless_revision transcripts extract --only s35e33
.venv/bin/python -m pointless_revision transcripts extract --batch

# Merge data/episodes/*.json into data/evidence.json + match-rate report:
python3 -m pointless_revision transcripts merge
python3 scripts/build_data.py              # picks up evidence + writes docs/data/episodes.json
python3 scripts/category_roadmap.py        # ranks unmatched rounds as new-category candidates
```

Notes: `.partial.srt` files (in-progress downloads) are skipped; extraction reruns skip episodes that already have output; subtitle font colours are used to attribute lines to host / co-host / contestants. Only derived facts plus a one-line evidence quote are stored — raw transcripts stay out of the published site.

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
