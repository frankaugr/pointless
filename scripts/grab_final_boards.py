"""Recover the four final-round category cards for each episode via frame OCR.

The four cards are on-screen text that the subtitles never carry. For each
episode this script:

1. parses the .srt to locate the board-reveal moment (the reveal line, or the
   longest subtitle gap inside the final segment),
2. downloads a ~60s clip around that moment with get_iplayer (skipped if the
   clip is already in videos/),
3. samples a frame every 2.5s and OCRs each with macOS Vision,
4. accepts the earliest frame whose text clusters into exactly four card
   "pills", and writes the titles to data/final_boards.json plus the winning
   frame to data/final_boards/<episode>.jpg for spot-checking.

Run `.venv/bin/python scripts/grab_final_boards.py` (needs pyobjc-framework-
Vision, ffmpeg, get_iplayer). Re-runs skip episodes already in the JSON.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import Quartz
import Vision
from Foundation import NSURL

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS = ROOT / "pointless_transcripts"
VIDEOS = ROOT / "videos"
FRAMES_DIR = ROOT / "data" / "final_boards"
BOARDS_JSON = ROOT / "data" / "final_boards.json"
PROFILE_DIR = ROOT / ".get_iplayer"

FINAL_START = re.compile(r"(?:for|to)\s+(?:the|our)\s*pointless\s*final", re.IGNORECASE)
REVEAL = re.compile(
    r"today's selection|tonight's selection|offer you|choose from|"
    r"four options|four categories|our four|four things|today's choices",
    re.IGNORECASE,
)
TAGS = re.compile(r"<[^>]*>")

CLIP_BEFORE = 15  # seconds of clip before the reveal anchor
CLIP_AFTER = 45
FRAME_STEP = 2.5
NOISE_STRINGS = {"POINTLESS", "POIINTLESS", "BBC", "B BC"}


def srt_time(ts: str) -> float:
    h, m, rest = ts.strip().split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_blocks(path: Path) -> list[tuple[float, float, str]]:
    blocks = []
    raw = path.read_text(encoding="utf-8", errors="replace")
    for chunk in re.split(r"\n\s*\n", raw):
        lines = [l for l in chunk.strip().splitlines() if l.strip()]
        if len(lines) < 2 or "-->" not in lines[1]:
            continue
        start, end = (srt_time(t) for t in lines[1].split("-->"))
        text = TAGS.sub("", " ".join(lines[2:])).strip()
        blocks.append((start, end, text))
    return blocks


def find_anchor(blocks: list[tuple[float, float, str]]) -> float | None:
    """Time (s) just before the category board appears."""
    starts = [i for i, b in enumerate(blocks) if FINAL_START.search(b[2])]
    if not starts:
        return None
    i0 = starts[-1]
    window = blocks[i0 : i0 + 60]
    for start, end, text in window:
        if REVEAL.search(text):
            return end
    # Fallback: longest gap between consecutive subtitles in the final segment.
    best_gap, anchor = 0.0, None
    for (s1, e1, _), (s2, _, _) in zip(window, window[1:]):
        if s2 - e1 > best_gap:
            best_gap, anchor = s2 - e1, e1
    return anchor


def episode_index() -> list[dict]:
    eps = []
    for srt in sorted(TRANSCRIPTS.glob("s[0-9][0-9]/*.srt")):
        if ".partial." in srt.name:
            continue
        m = re.search(r"(s\d+e\d+)-([a-z0-9]+)\.srt$", srt.name)
        if m:
            eps.append({"id": m.group(1), "pid": m.group(2), "srt": srt})
    return eps


def find_clip(pid: str) -> Path | None:
    hits = sorted(VIDEOS.glob(f"*{pid}*.mp4"))
    return hits[0] if hits else None


def download_clip(pid: str, anchor: float) -> Path | None:
    start = max(0, int(anchor - CLIP_BEFORE))
    cmd = [
        "get_iplayer",
        f"--profile-dir={PROFILE_DIR}",
        f"--pid={pid}",
        "--quality=sd",
        f"--output={VIDEOS}",
        f"--start={start}",
        f"--stop={int(anchor + CLIP_AFTER)}",
        "--force",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    clip = find_clip(pid)
    if clip is None:
        sys.stderr.write(res.stdout[-2000:] + res.stderr[-2000:])
    return clip


def extract_frames(clip: Path, outdir: Path) -> list[tuple[float, Path]]:
    outdir.mkdir(parents=True, exist_ok=True)
    pattern = outdir / "frame_%03d.jpg"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(clip), "-vf",
         f"fps=1/{FRAME_STEP}", "-q:v", "2", str(pattern), "-y"],
        check=True, timeout=300,
    )
    frames = sorted(outdir.glob("frame_*.jpg"))
    return [((int(f.stem.split("_")[1]) - 1) * FRAME_STEP, f) for f in frames]


def ocr_observations(path: Path) -> list[dict]:
    url = NSURL.fileURLWithPath_(str(path))
    src = Quartz.CGImageSourceCreateWithURL(url, None)
    if src is None:
        return []
    img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setUsesLanguageCorrection_(False)
    handler.performRequests_error_([req], None)
    out = []
    for obs in req.results() or []:
        cand = obs.topCandidates_(1)[0]
        box = obs.boundingBox()
        out.append(
            {
                "text": cand.string().strip(),
                "conf": float(cand.confidence()),
                "x_center": box.origin.x + box.size.width / 2,
                "y_center": box.origin.y + box.size.height / 2,
                "height": box.size.height,
            }
        )
    return out


def board_pills(observations: list[dict]) -> list[dict]:
    """Cluster card-like OCR lines into pills, top to bottom."""
    cards = []
    for o in observations:
        letters = [c for c in o["text"] if c.isalpha()]
        if len(letters) < 3:
            continue
        upper = sum(c.isupper() for c in letters) / len(letters)
        if upper < 0.7:
            continue
        if o["text"].upper() in NOISE_STRINGS:
            continue
        if not (0.35 <= o["x_center"] <= 0.95 and 0.10 <= o["y_center"] <= 0.90):
            continue
        if not (0.015 <= o["height"] <= 0.09):
            continue
        cards.append(o)
    cards.sort(key=lambda o: -o["y_center"])
    pills = []
    for o in cards:
        if pills and pills[-1][-1]["y_center"] - o["y_center"] < 0.055:
            pills[-1].append(o)
        else:
            pills.append([o])
    return [
        {
            "title": " ".join(p["text"] for p in pill),
            "conf": min(p["conf"] for p in pill),
        }
        for pill in pills
    ]


def read_board(clip: Path) -> dict:
    """OCR sampled frames; return the earliest clean four-pill board."""
    with tempfile.TemporaryDirectory() as td:
        frames = extract_frames(clip, Path(td))
        fallback = None
        for offset, frame in frames:
            pills = board_pills(ocr_observations(frame))
            if len(pills) != 4:
                continue
            result = {
                "cards": [p["title"] for p in pills],
                "min_conf": round(min(p["conf"] for p in pills), 2),
                "offset": offset,
                "frame": frame.read_bytes(),
            }
            if result["min_conf"] >= 0.8:
                return result
            if fallback is None or result["min_conf"] > fallback["min_conf"]:
                fallback = result
        return fallback or {}


def process(ep: dict, skip_download: bool) -> dict:
    anchor = find_anchor(parse_blocks(ep["srt"]))
    if anchor is None:
        return {"status": "no_anchor"}
    clip = find_clip(ep["pid"])
    if clip is None and not skip_download:
        clip = download_clip(ep["pid"], anchor)
    if clip is None:
        return {"status": "no_clip", "anchor": anchor}
    board = read_board(clip)
    if not board:
        return {"status": "no_board", "anchor": anchor, "clip": clip.name}
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    frame_path = FRAMES_DIR / f"{ep['id']}.jpg"
    frame_path.write_bytes(board.pop("frame"))
    status = "ok" if board["min_conf"] >= 0.8 else "low_conf"
    return {"status": status, "anchor": anchor, "clip": clip.name, **board}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="comma-separated episode ids, e.g. s34e05")
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--redo", action="store_true", help="reprocess episodes already in the JSON")
    args = ap.parse_args()

    boards = json.loads(BOARDS_JSON.read_text()) if BOARDS_JSON.exists() else {}
    only = set(args.only.split(",")) if args.only else None
    eps = [e for e in episode_index() if only is None or e["id"] in only]
    VIDEOS.mkdir(exist_ok=True)

    for ep in eps:
        if not args.redo and boards.get(ep["id"], {}).get("status") == "ok":
            continue
        result = process(ep, args.skip_download)
        boards[ep["id"]] = result
        BOARDS_JSON.write_text(json.dumps(boards, indent=2, sort_keys=True) + "\n")
        cards = " | ".join(result.get("cards", []))
        print(f"{ep['id']}  {result['status']:<8}  {cards}", flush=True)

    bad = {k: v["status"] for k, v in boards.items() if v.get("status") != "ok"}
    print(f"\n{len(boards) - len(bad)}/{len(boards)} boards read cleanly."
          + (f" Needs review: {bad}" if bad else ""))


if __name__ == "__main__":
    main()
