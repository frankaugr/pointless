"""Parse get_iplayer subtitle (.srt) files into speaker-attributed scripts.

BBC subtitle rips colour-code speakers, which is a reliable channel for
Pointless: white is the host (Alexander Armstrong), yellow the co-host's
desk recaps, cyan the contestants. The extraction prompt leans on this to
tell host reveals apart from contestant guesses and co-host recaps.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


SPEAKER_BY_COLOUR = {
    "ffffff": "HOST",
    "ffff00": "COHOST",
    "00ffff": "CONTESTANT",
}

FONT_SEGMENT = re.compile(r'<font color="#([0-9a-fA-F]{6})">(.*?)</font>', re.DOTALL)
TAG = re.compile(r"<[^>]+>")
TIMESTAMP = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->")
# Deliberately rejects in-progress downloads such as `...-m002wm6q.partial.srt`:
# the pid group cannot contain a dot.
EPISODE_FILENAME = re.compile(r"pointless-s(\d+)e(\d+)-([a-z0-9]+)\.srt$")


@dataclass(frozen=True)
class Segment:
    start_seconds: float
    speaker: str
    text: str


@dataclass(frozen=True)
class EpisodeFile:
    path: Path
    series: int
    episode: int
    pid: str

    @property
    def episode_id(self) -> str:
        return f"s{self.series:02d}e{self.episode:02d}"

    @property
    def episode_label(self) -> str:
        return f"Series {self.series} Episode {self.episode}"

    @property
    def bbc_url(self) -> str:
        return f"https://www.bbc.co.uk/programmes/{self.pid}"


def episode_file(path: Path) -> EpisodeFile | None:
    match = EPISODE_FILENAME.search(path.name)
    if not match:
        return None
    return EpisodeFile(
        path=path,
        series=int(match.group(1)),
        episode=int(match.group(2)),
        pid=match.group(3),
    )


def iter_episode_files(root: Path) -> list[EpisodeFile]:
    """All complete episode subtitle files under root, deduped by episode id."""
    by_id: dict[str, EpisodeFile] = {}
    for path in sorted(root.rglob("*.srt")):
        ep = episode_file(path)
        if ep is not None:
            by_id.setdefault(ep.episode_id, ep)
    return sorted(by_id.values(), key=lambda ep: (ep.series, ep.episode))


def parse_segments(srt_text: str) -> list[Segment]:
    segments: list[Segment] = []
    for block in re.split(r"\n\s*\n", srt_text):
        lines = [line.strip() for line in block.strip().splitlines()]
        if not lines:
            continue
        start = None
        content_lines: list[str] = []
        for line in lines:
            ts = TIMESTAMP.search(line)
            if ts:
                hours, minutes, seconds, millis = (int(g) for g in ts.groups())
                start = hours * 3600 + minutes * 60 + seconds + millis / 1000
            elif start is not None:
                content_lines.append(line)
        if start is None or not content_lines:
            continue

        for line in content_lines:
            matched_any = False
            for colour, text in FONT_SEGMENT.findall(line):
                matched_any = True
                text = _clean(text)
                if text:
                    speaker = SPEAKER_BY_COLOUR.get(colour.lower(), "OTHER")
                    segments.append(Segment(start, speaker, text))
            if not matched_any:
                text = _clean(TAG.sub("", line))
                if text:
                    segments.append(Segment(start, "OTHER", text))
    return segments


def build_script(segments: list[Segment]) -> str:
    """Collapse segments into `[mm:ss] SPEAKER: ...` lines, one per speaker turn."""
    lines: list[str] = []
    current_speaker = None
    current_start = 0.0
    current_text: list[str] = []

    def flush() -> None:
        if current_speaker is not None and current_text:
            minutes, seconds = divmod(int(current_start), 60)
            lines.append(f"[{minutes:02d}:{seconds:02d}] {current_speaker}: {' '.join(current_text)}")

    for segment in segments:
        if segment.speaker != current_speaker:
            flush()
            current_speaker = segment.speaker
            current_start = segment.start_seconds
            current_text = []
        current_text.append(segment.text)
    flush()
    return "\n".join(lines)


def script_for(path: Path) -> str:
    return build_script(parse_segments(path.read_text(encoding="utf-8", errors="replace")))


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
