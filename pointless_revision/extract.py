"""Extract structured round/answer/score facts from episode scripts via Claude.

The anthropic SDK is imported lazily so the rest of the CLI stays
dependency-free. Single-episode mode is for prompt iteration; batch mode
(50% cheaper) is for the full corpus.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any

from .transcripts import EpisodeFile, script_for


MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """You extract structured data from subtitle transcripts of the BBC quiz show Pointless.

Show format: 100 people were given 100 seconds to name as many answers as they could in a category. Contestants give answers; an answer scores the number of surveyed people who said it (0-100). A score of 0 is a "pointless answer". Wrong answers score 100. The pair with the highest round total is eliminated. Rounds: two opening rounds, a head-to-head, then a final where the winning pair picks a category and gives three answers trying to find at least one pointless answer for the jackpot.

Transcript format: `[mm:ss] SPEAKER: text`. HOST is Alexander Armstrong (reads questions, names contestants' answers, reacts to the countdown). COHOST runs the desk recaps (explains answers, reads out the pointless answers and the lowest-scoring answers after each pass). CONTESTANT lines are the players.

Extract every round you can identify. For each round:

- category_text: the category as the show framed it. The on-screen question text is usually NOT spoken — reconstruct it from context (host framing, co-host explanation, the answers given). Set category_confidence accordingly: "high" if the category is spoken or unambiguous from multiple cues, "medium" if confidently inferred, "low" if a guess.
- facts: one entry per (answer, score) you can support from the dialogue.

Fact rules:
- kind "guess": a contestant's answer. Record score only when the dialogue states it ("57 of our 100", "down to 23", "scores you 12"). The board total is often unspoken — use null rather than guessing.
- kind "recap_pointless": answers the co-host lists as pointless answers (score 0).
- kind "recap_lowest": answers the co-host names as the lowest scorers, with their stated scores.
- kind "recap_other": other answer/score pairs stated in recaps.
- kind "jackpot_answer": the final-round answers, with revealed scores.
- is_pointless: true when the dialogue confirms the answer was pointless.
- is_incorrect: true when the answer was wrong / not on the board (these score 100 in-game but are NOT survey data — still record them, flagged).
- evidence_quote: a short verbatim snippet (max ~120 characters) of the line supporting the score.
- contestant: first name if attributable, else null.

Only record what the dialogue supports. Never invent scores. Prefer fewer, well-supported facts over coverage."""

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rounds": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "round_label": {
                        "type": "string",
                        "description": "e.g. 'Round 1', 'Round 2', 'Head-to-head', 'Final'",
                    },
                    "category_text": {"type": "string"},
                    "category_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "facts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "answer": {"type": "string"},
                                "score": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                                "is_pointless": {"type": "boolean"},
                                "is_incorrect": {"type": "boolean"},
                                "kind": {
                                    "type": "string",
                                    "enum": [
                                        "guess",
                                        "recap_pointless",
                                        "recap_lowest",
                                        "recap_other",
                                        "jackpot_answer",
                                    ],
                                },
                                "contestant": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                                "evidence_quote": {"type": "string"},
                            },
                            "required": [
                                "answer",
                                "score",
                                "is_pointless",
                                "is_incorrect",
                                "kind",
                                "contestant",
                                "evidence_quote",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["round_label", "category_text", "category_confidence", "facts"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["rounds"],
    "additionalProperties": False,
}


def request_params(script: str, episode_label: str) -> dict[str, Any]:
    return {
        "model": MODEL,
        "max_tokens": 16000,
        "thinking": {"type": "adaptive"},
        "system": [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "output_config": {"format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}},
        "messages": [
            {"role": "user", "content": f"Transcript of {episode_label}:\n\n{script}"}
        ],
    }


def _payload(ep: EpisodeFile, rounds: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "episode_id": ep.episode_id,
        "episode_label": ep.episode_label,
        "series": ep.series,
        "episode": ep.episode,
        "pid": ep.pid,
        "source_url": ep.bbc_url,
        "model": MODEL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rounds": rounds,
    }


def _rounds_from_message(message: Any) -> list[dict[str, Any]]:
    text = next(block.text for block in message.content if block.type == "text")
    return json.loads(text)["rounds"]


def _write(out_dir: Path, payload: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{payload['episode_id']}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def extract_episode(client: Any, ep: EpisodeFile, out_dir: Path) -> Path:
    message = client.messages.create(**request_params(script_for(ep.path), ep.episode_label))
    return _write(out_dir, _payload(ep, _rounds_from_message(message)))


CLASSIFY_SYSTEM_PROMPT = """You classify Pointless quiz-show round descriptions by question format.

A round is "open_recall" only if it follows the canonical format: contestants were asked to name as many members of a category as they could, from memory alone — "name any X" / "name as many X where Y". A qualifying constraint (beginning with a letter, within a date range, geographic, etc.) is still open recall.

A round is NOT open_recall when the board assists or reverses the task: identifying answers from pictures, drawings, clues, definitions, initials, or descriptions; choosing among presented options ("which of these six...", "spot the pointless..."); wordplay reconstruction (anagrams, letters removed/changed/swapped, alternate letters, fill in blanks, hidden words); reverse lookups ("name the artist given these songs", "facts about X"); or multi-part hybrid boards.

When the description is ambiguous, classify as not open_recall."""

CLASSIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "classifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "open_recall": {"type": "boolean"},
                },
                "required": ["id", "open_recall"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["classifications"],
    "additionalProperties": False,
}


def classify_rounds(client: Any, episodes_dir: Path) -> dict[str, int]:
    """Annotate every round in episodes_dir with question_format.

    One request classifies all round descriptions; results are written back
    into the episode JSON files as `question_format: "open_recall" | "assisted"`.
    """
    episodes = {
        path: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(episodes_dir.glob("*.json"))
    }
    lines = []
    for path, episode in episodes.items():
        for idx, round_data in enumerate(episode.get("rounds", [])):
            lines.append(f"{episode['episode_id']}:{idx} | {round_data.get('category_text', '')}")

    verdicts: dict[str, bool] = {}
    chunk_size = 150
    for start in range(0, len(lines), chunk_size):
        chunk = lines[start : start + chunk_size]
        with client.messages.stream(
            model=MODEL,
            max_tokens=64000,
            thinking={"type": "adaptive"},
            system=CLASSIFY_SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": CLASSIFY_SCHEMA}},
            messages=[
                {
                    "role": "user",
                    "content": "Classify every round below. Echo each id exactly.\n\n" + "\n".join(chunk),
                }
            ],
        ) as stream:
            message = stream.get_final_message()
        if message.stop_reason != "end_turn":
            raise RuntimeError(f"classification stopped early: {message.stop_reason}")
        text = next(block.text for block in message.content if block.type == "text")
        for item in json.loads(text)["classifications"]:
            verdicts[item["id"]] = item["open_recall"]
        print(f"  classified {min(start + chunk_size, len(lines))}/{len(lines)} rounds")

    tally = {"open_recall": 0, "assisted": 0, "missing": 0}
    for path, episode in episodes.items():
        for idx, round_data in enumerate(episode.get("rounds", [])):
            verdict = verdicts.get(f"{episode['episode_id']}:{idx}")
            if verdict is None:
                tally["missing"] += 1
                continue
            round_data["question_format"] = "open_recall" if verdict else "assisted"
            tally["open_recall" if verdict else "assisted"] += 1
        path.write_text(json.dumps(episode, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return tally


def run_batch(client: Any, episodes: list[EpisodeFile], out_dir: Path, poll_seconds: int = 60) -> dict[str, int]:
    """Submit one batch for all episodes, poll to completion, write results.

    Returns {"succeeded": n, "errored": n}. Episodes that already have an
    output file are skipped so reruns only pay for what is missing.
    """
    pending = [ep for ep in episodes if not (out_dir / f"{ep.episode_id}.json").exists()]
    if not pending:
        return {"succeeded": 0, "errored": 0}

    batch = client.messages.batches.create(
        requests=[
            {
                "custom_id": ep.episode_id,
                "params": request_params(script_for(ep.path), ep.episode_label),
            }
            for ep in pending
        ]
    )
    print(f"Submitted batch {batch.id} with {len(pending)} episodes.")

    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        counts = batch.request_counts
        print(
            f"  {batch.processing_status}: {counts.processing} processing, "
            f"{counts.succeeded} succeeded, {counts.errored} errored"
        )
        time.sleep(poll_seconds)

    by_id = {ep.episode_id: ep for ep in pending}
    tally = {"succeeded": 0, "errored": 0}
    for result in client.messages.batches.results(batch.id):
        ep = by_id[result.custom_id]
        if result.result.type == "succeeded":
            _write(out_dir, _payload(ep, _rounds_from_message(result.result.message)))
            tally["succeeded"] += 1
        else:
            tally["errored"] += 1
            print(f"  {result.custom_id}: {result.result.type}")
    return tally
