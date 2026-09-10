# Pointless Revision

A static revision tool for recurring Pointless-style answer sets.

- Memorise (the opening screen): short sessions of 5, 10 or 20 cards, facts-to-name or name-to-facts recall, optional typed answers and hints, personal memory cues, and spaced review. Start with Sportspeople or Politicians, or choose any existing category. Study the deck provides searchable cards. Progress stays in this browser and can be exported/imported as JSON.

- Learn: browse finite categories, sort by obscurity, hide/reveal answers, and mark answers as known or needing work. Answers seen on the show carry an expandable evidence panel (score, episode, question, quote).
- Revise: answer generated narrowed prompts such as chemical elements by name pattern, countries by continent, or US state capitals containing selected letters.
- Play: real rounds from series 34-35 — give answers against the actual category, then compare with what the surveyed 100 said. Boards are limited to answers spoken aloud in each episode.
- Finals: the final-round category cards offered in series 34-35 and never chosen — still in the show's rotation — with inferred question wordings and candidate pointless answers (curated in `data/final_pool_inferences.json`).
- Cheat sheet: the existing selected sporting answers, also used as the source of Memorise's sports cards. These are selected study targets, not complete sports answer sets or verified low survey scorers.

## Memory practice

The memory deck derives sports cards from the cheat sheet and other cards from the exported category attributes; it does not modify the curated fixtures or fabricate scores. Politicians includes all 58 UK prime ministers and 45 distinct US presidents in the existing data. All scores are included in recall sessions.

Overdue reviews come before unseen cards. Again schedules 10 minutes and adds one same-session retry per missed card; With effort schedules 1 day; Remembered starts at 3 days and doubles up to 180 days. Any-cards practice can include future reviews. Ratings are self-assessed, and both recall directions share a schedule. Existing Learn-mode marks remain separate. Backups are validated before merging, preserving the more recently reviewed record per card. Personal notes are plain text and browser-local.

GitHub Pages publishes `docs/` from `main`; the repository's default research branch is older. Preserve the service worker asset list and bump its cache version when changing the app shell.

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
python3 -m pointless_revision transcripts classify   # tag open-recall vs assisted rounds (API)
python3 -m pointless_revision transcripts merge
python3 scripts/build_data.py              # picks up evidence + writes docs/data/episodes.json
python3 scripts/category_roadmap.py        # ranks unmatched rounds as new-category candidates
```

Notes: `.partial.srt` files (in-progress downloads) are skipped; extraction reruns skip episodes that already have output; subtitle font colours are used to attribute lines to host / co-host / contestants. Only derived facts plus a one-line evidence quote are stored — raw transcripts stay out of the published site.

## Final-Round Board Pool

The four final-round category cards are on-screen text the subtitles never carry. Two scripts recover them per episode (needs `get_iplayer`, `ffmpeg`, and `pip install pyobjc-framework-Vision`):

```sh
.venv/bin/python scripts/grab_final_boards.py    # ~60s clip per episode + Vision OCR -> data/final_boards.json
.venv/bin/python scripts/final_pool_report.py    # infer chosen card, build pool ledger -> data/final_pool.json + data/final_board_pool.md
```

Clips land in `videos/` and the winning frame per episode in `data/final_boards/` (both untracked); re-runs skip episodes already read cleanly. `scripts/dump_final_windows.py` prints each episode's final-round deliberation dialogue for manual checks.

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
