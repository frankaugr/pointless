"""Dump the final-round category-selection window from each transcript.

For each episode .srt, locate the start of the Pointless final, then print the
subtitle blocks covering the category board reveal and the pair's deliberation,
stopping once the co-host starts defining the chosen question. The output is a
plain-text digest meant for manual review, not a parsed data file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TRANSCRIPTS = Path(__file__).resolve().parent.parent / "pointless_transcripts"

FINAL_START = re.compile(r"(?:for|to)\s+(?:the|our)\s*pointless\s*final", re.IGNORECASE)
REVEAL = re.compile(
    r"today's selection|tonight's selection|offer you|choose from|"
    r"four options|four categories|our four|four things|today's choices",
    re.IGNORECASE,
)
QUESTION_DEF = re.compile(r"looking for|we want the name|we would like", re.IGNORECASE)

FONT_TAG = re.compile(r'<font color="(#[0-9a-fA-F]{6})">')
TAGS = re.compile(r"<[^>]*>")

SPEAKERS = {
    "#ffffff": "HOST",
    "#ffff00": "COHOST",
}


def parse_blocks(path: Path) -> list[tuple[str, str]]:
    """Return (timestamp, text-with-speaker-prefixes) per subtitle block."""
    blocks = []
    raw = path.read_text(encoding="utf-8", errors="replace")
    for chunk in re.split(r"\n\s*\n", raw):
        lines = [l for l in chunk.strip().splitlines() if l.strip()]
        if len(lines) < 2 or "-->" not in lines[1]:
            continue
        time = lines[1].split("-->")[0].strip()
        body = " ".join(lines[2:])
        colours = FONT_TAG.findall(body)
        speaker = SPEAKERS.get(colours[0], "PAIR") if colours else "?"
        text = TAGS.sub("", body).strip()
        blocks.append((time, f"[{speaker}] {text}"))
    return blocks


def dump_episode(path: Path) -> str:
    blocks = parse_blocks(path)
    matches = [i for i, (_, t) in enumerate(blocks) if FINAL_START.search(t)]
    start = matches[-1] if matches else None
    if start is None:
        return "  !! final-start marker not found\n"
    reveal = next(
        (i for i in range(start, min(start + 60, len(blocks))) if REVEAL.search(blocks[i][1])),
        None,
    )
    if reveal is None:
        reveal = start
    end = next(
        (
            i
            for i in range(reveal + 1, min(reveal + 40, len(blocks)))
            if QUESTION_DEF.search(blocks[i][1])
        ),
        min(reveal + 30, len(blocks) - 1),
    )
    out = []
    for time, text in blocks[max(reveal - 3, start) : end + 3]:
        out.append(f"  {time}  {text}")
    return "\n".join(out) + "\n"


def main() -> None:
    for series_dir in sorted(TRANSCRIPTS.glob("s[0-9][0-9]")):
        for srt in sorted(series_dir.glob("*.srt")):
            if ".partial." in srt.name:
                continue
            ep = re.search(r"(s\d+e\d+)", srt.name)
            print(f"=== {ep.group(1) if ep else srt.name} ===")
            print(dump_episode(srt))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
