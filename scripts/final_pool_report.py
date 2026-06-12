"""Aggregate OCR'd final boards into a card-pool ledger.

Reads data/final_boards.json (from grab_final_boards.py) and the per-episode
extractions in data/episodes/*.json, identifies which of the four cards the
winning pair chose, and reports every card's history: episodes where it was
offered, and the episode (if any) where it was chosen and so left the pool.

The chosen card is inferred per episode by scoring each card title against
(a) the extracted final-round question text and (b) the post-reveal dialogue
in the transcript, where the host always echoes the chosen title. Episodes
where the top two scores are close are flagged for manual review.

Writes data/final_pool.json and prints a summary table.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARDS_JSON = ROOT / "data" / "final_boards.json"
EPISODES_DIR = ROOT / "data" / "episodes"
TRANSCRIPTS = ROOT / "pointless_transcripts"
OUT_JSON = ROOT / "data" / "final_pool.json"
OUT_MD = ROOT / "data" / "final_board_pool.md"

STOPWORDS = {
    "THE", "OF", "A", "AND", "OR", "IN", "ON", "TO", "FOR", "ANY", "WITH",
    "AT", "BY", "FROM", "THAT", "THIS", "IT", "IS", "ARE",
}
TAGS = re.compile(r"<[^>]*>")


def norm_key(title: str) -> str:
    """Canonical identity for a card across episodes despite OCR variance."""
    return re.sub(r"[^A-Z0-9]", "", title.upper())


def clean_title(title: str) -> str:
    """Normalise OCR quote noise in a card title."""
    return re.sub(r"['\"]+", "'", title)


ACRONYMS = {"TV", "UK", "US", "AM", "PM"}


def display_title(title: str) -> str:
    """Title-case an all-caps card without mangling possessives or numbers."""
    words = []
    for w in title.split():
        bare = re.sub(r"[^A-Z0-9]", "", w.upper())
        if bare in ACRONYMS:
            words.append(w.upper())
            continue
        for i, c in enumerate(w):
            if c.isalpha():
                w = w[:i] + c.upper() + w[i + 1 :].lower()
                break
        words.append(w)
    return " ".join(words)


def tokens(text: str) -> set[str]:
    """Punctuation-folded tokens, with singular variants for plural words."""
    out = set()
    for raw in re.findall(r"[A-Za-z0-9']+", text):
        t = re.sub(r"[^A-Z0-9]", "", raw.upper())
        if not t or t in STOPWORDS:
            continue
        out.add(t)
        if t.endswith("S") and len(t) > 3:
            out.add(t[:-1])
    return out


def final_category_text(episode_id: str) -> str:
    path = EPISODES_DIR / f"{episode_id}.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text())
    for r in data.get("rounds", []):
        if r.get("round_label", "").lower().startswith("final"):
            return r.get("category_text", "")
    return ""


DIALOGUE_WINDOW = 240  # seconds of final-round talk to scan after the reveal


def post_reveal_blocks(episode_id: str, anchor: float) -> list[tuple[float, set[str]]]:
    hits = list(TRANSCRIPTS.glob(f"s*/{'pointless-' + episode_id}-*.srt"))
    if not hits:
        return []
    raw = hits[0].read_text(encoding="utf-8", errors="replace")
    out = []
    for chunk in re.split(r"\n\s*\n", raw):
        lines = [l for l in chunk.strip().splitlines() if l.strip()]
        if len(lines) < 2 or "-->" not in lines[1]:
            continue
        h, m, rest = lines[1].split("-->")[0].strip().split(":")
        start = int(h) * 3600 + int(m) * 60 + float(rest.replace(",", "."))
        if anchor <= start <= anchor + DIALOGUE_WINDOW:
            out.append((start, tokens(TAGS.sub("", " ".join(lines[2:])))))
    return out


def pick_chosen(cards: list[str], episode_id: str, anchor: float) -> tuple[int, bool]:
    """Return (index of chosen card, confident?).

    Signals: overlap with the extracted question text, overlap with the
    post-reveal dialogue, and recency — rejected cards stop being mentioned
    once the pair picks, while the chosen card is echoed by the host and
    discussed for the rest of the show.
    """
    question = tokens(final_category_text(episode_id))
    blocks = post_reveal_blocks(episode_id, anchor)
    dialogue = set().union(*(toks for _, toks in blocks)) if blocks else set()
    scores = []
    for card in cards:
        toks = tokens(card)
        if not toks:
            scores.append(0.0)
            continue
        need = min(2, len(toks))
        last_mention = max(
            (start for start, blk in blocks if len(toks & blk) >= need),
            default=None,
        )
        recency = (
            (last_mention - anchor) / DIALOGUE_WINDOW if last_mention else 0.0
        )
        q_overlap = len(toks & question) / len(toks)
        d_overlap = len(toks & dialogue) / len(toks)
        scores.append(2 * q_overlap + d_overlap + 2 * recency)
    ranked = sorted(range(len(scores)), key=lambda i: -scores[i])
    best, second = ranked[0], ranked[1]
    confident = scores[best] > 1.0 and scores[best] - scores[second] >= 0.5
    return best, confident


def merge_ocr_variants(pool: dict[str, dict], review: list[str]) -> None:
    """Fold nearly identical keys (stray OCR characters) into one card."""
    keys = sorted(pool, key=lambda k: -len(pool[k]["offered"]))
    for key in list(keys):
        if key not in pool:
            continue
        for other in list(pool):
            if other == key or other not in pool:
                continue
            if difflib.SequenceMatcher(None, key, other).ratio() < 0.9:
                continue
            a, b = pool[key], pool.pop(other)
            review.append(f"merged OCR variants: {a['title']!r} <- {b['title']!r}")
            a["offered"] = sorted(set(a["offered"]) | set(b["offered"]))
            a["chosen_in"] = a["chosen_in"] or b["chosen_in"]


def main() -> None:
    boards = json.loads(BOARDS_JSON.read_text())
    pool: dict[str, dict] = {}
    review: list[str] = []

    for ep_id in sorted(boards):
        entry = boards[ep_id]
        cards = entry.get("cards")
        if not cards:
            review.append(f"{ep_id}: board not read ({entry.get('status')})")
            continue
        chosen_idx, confident = pick_chosen(cards, ep_id, entry.get("anchor", 0))
        if not confident:
            review.append(f"{ep_id}: unsure which card was chosen: {cards}")
        for i, card in enumerate(cards):
            key = norm_key(card)
            card = clean_title(card)
            rec = pool.setdefault(
                key, {"title": card, "offered": [], "chosen_in": None}
            )
            if len(card) > len(rec["title"]):
                rec["title"] = card
            rec["offered"].append(ep_id)
            if i == chosen_idx:
                rec["chosen_in"] = ep_id
                rec["chosen_confident"] = confident

    merge_ocr_variants(pool, review)
    for rec in pool.values():
        rec["title"] = display_title(rec["title"])

    in_play = {k: v for k, v in pool.items() if v["chosen_in"] is None}
    retired = {k: v for k, v in pool.items() if v["chosen_in"] is not None}

    OUT_JSON.write_text(json.dumps(
        {
            "cards": pool,
            "in_play_count": len(in_play),
            "retired_count": len(retired),
            "needs_review": review,
        },
        indent=2, sort_keys=True) + "\n")

    print(f"{len(pool)} distinct cards seen across {len(boards)} boards")
    print(f"\n== Still in play ({len(in_play)}) ==")
    for rec in sorted(in_play.values(), key=lambda r: (-len(r["offered"]), r["title"])):
        print(f"  {rec['title']}  [{', '.join(rec['offered'])}]")
    print(f"\n== Retired ({len(retired)}) ==")
    for rec in sorted(retired.values(), key=lambda r: r["chosen_in"]):
        offered_first = [e for e in rec["offered"] if e != rec["chosen_in"]]
        extra = f" (offered {', '.join(offered_first)})" if offered_first else ""
        print(f"  {rec['chosen_in']}: {rec['title']}{extra}")
    if review:
        print(f"\n== Needs review ({len(review)}) ==")
        for line in review:
            print(f"  {line}")
    write_markdown(boards, in_play, retired, review)


def write_markdown(boards, in_play, retired, review) -> None:
    lines = [
        "# Final-round category pool (series 34-35)",
        "",
        "Generated by `scripts/final_pool_report.py` from frame OCR of every",
        f"final-round board ({len(boards)} episodes, see `scripts/grab_final_boards.py`).",
        "Each board offers four cards; the chosen card leaves the pool, the other",
        "three return for future shows. The pool carries over between series:",
        "every cross-series reuse below is direct evidence.",
        "",
        f"## Still in play ({len(in_play)})",
        "",
        "Offered at least once, never chosen, as of the last episode in the corpus.",
        "",
        "| Card | Times offered | Episodes |",
        "| --- | --- | --- |",
    ]
    for rec in sorted(in_play.values(), key=lambda r: (-len(r["offered"]), r["title"])):
        lines.append(
            f"| {rec['title']} | {len(rec['offered'])} | {', '.join(rec['offered'])} |"
        )
    lines += [
        "",
        f"## Retired ({len(retired)})",
        "",
        "Chosen by the winning pair; earlier unchosen offers in brackets.",
        "",
        "| Chosen in | Card | Offered earlier |",
        "| --- | --- | --- |",
    ]
    for rec in sorted(retired.values(), key=lambda r: r["chosen_in"]):
        offered_first = [e for e in rec["offered"] if e != rec["chosen_in"]]
        lines.append(
            f"| {rec['chosen_in']} | {rec['title']} | {', '.join(offered_first)} |"
        )
    if review:
        lines += ["", "## Notes", ""] + [f"- {r}" for r in review]
    OUT_MD.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
