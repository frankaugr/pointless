from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .categories import CATEGORIES
from .export import build_payloads, write_static_data


def cmd_categories(_args) -> int:
    for slug, category in CATEGORIES.items():
        print(f"{slug:28s}  {category.name:34s}  {len(category.answers):3d}")
    return 0


def cmd_validate(_args) -> int:
    build_payloads()
    print(f"Validated {len(CATEGORIES)} categories.")
    return 0


def cmd_build(args) -> int:
    write_static_data(args.out_dir)
    print(f"Wrote static JSON to {args.out_dir}.")
    return 0


def cmd_show(args) -> int:
    _index, payloads = build_payloads()
    payload = payloads.get(args.category)
    if payload is None:
        print(f"Unknown category: {args.category}", file=sys.stderr)
        return 1

    print(f"{payload['name']} ({payload['n_answers']} answers)")
    print(f"{'pts':>3s}  {'conf':>6s}  {'answer':40s}  details")
    print("-" * 86)
    for item in payload["answers"][: args.limit]:
        details = ", ".join(
            f"{field}={item['attrs'].get(field)}"
            for field in payload["display_fields"]
            if item["attrs"].get(field) not in (None, "")
        )
        print(
            f"{item['obscurity'].get('pointless_score', round((1 - item['obscurity']['score']) * 100)):3d}  "
            f"{item['obscurity']['confidence']:>6s}  "
            f"{item['name'][:40]:40s}  {details}"
        )
    return 0


def cmd_ts_script(args) -> int:
    from .transcripts import script_for

    print(script_for(args.srt_path))
    return 0


def cmd_ts_extract(args) -> int:
    from .extract import extract_episode, run_batch
    from .transcripts import iter_episode_files

    try:
        import anthropic
    except ImportError:
        print("The `anthropic` package is required: .venv/bin/pip install anthropic", file=sys.stderr)
        return 1

    episodes = iter_episode_files(args.root)
    if args.only:
        wanted = set(args.only)
        episodes = [ep for ep in episodes if ep.episode_id in wanted]
    if args.limit:
        episodes = episodes[: args.limit]
    if not episodes:
        print("No matching episodes found.", file=sys.stderr)
        return 1

    client = anthropic.Anthropic()
    if args.batch:
        tally = run_batch(client, episodes, args.out)
        print(f"Batch done: {tally['succeeded']} succeeded, {tally['errored']} errored.")
        return 1 if tally["errored"] else 0

    for ep in episodes:
        path = extract_episode(client, ep, args.out)
        print(f"{ep.episode_id} -> {path}")
    return 0


def cmd_ts_classify(args) -> int:
    from .extract import classify_rounds

    try:
        import anthropic
    except ImportError:
        print("The `anthropic` package is required: .venv/bin/pip install anthropic", file=sys.stderr)
        return 1

    tally = classify_rounds(anthropic.Anthropic(), args.episodes)
    print(
        f"Classified rounds: {tally['open_recall']} open recall, "
        f"{tally['assisted']} assisted, {tally['missing']} missing verdicts"
    )
    return 1 if tally["missing"] else 0


def cmd_ts_merge(args) -> int:
    from .evidence import merge_episodes, write_evidence

    records, report = merge_episodes(args.episodes)
    write_evidence(records, args.out)
    print(f"Wrote {len(records)} evidence records to {args.out}")
    print(
        f"Episodes: {report['episodes']}  rounds: {report['rounds']}  "
        f"matched to curated categories: {report['rounds_matched']}"
    )
    print(
        f"Facts recorded: {report['facts_recorded']}  "
        f"skipped (incorrect): {report['facts_skipped_incorrect']}  "
        f"skipped (no score): {report['facts_skipped_no_score']}"
    )
    unmatched_answers = sum(len(v) for v in report["unmatched_answers"].values())
    print(f"Answers without a canonical match: {unmatched_answers}")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        import json

        args.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Full report: {args.report}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pointless_revision")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("categories", help="List curated categories").set_defaults(func=cmd_categories)
    sub.add_parser("validate", help="Validate category counts and export payloads").set_defaults(func=cmd_validate)

    p_build = sub.add_parser("build", help="Write docs/data JSON from curated fixtures")
    p_build.add_argument("--out-dir", type=Path, default=Path("docs/data"))
    p_build.set_defaults(func=cmd_build)

    p_show = sub.add_parser("show", help="Show answers ranked by obscurity")
    p_show.add_argument("category")
    p_show.add_argument("--limit", type=int, default=25)
    p_show.set_defaults(func=cmd_show)

    p_ts = sub.add_parser("transcripts", help="Subtitle transcript extraction pipeline")
    ts_sub = p_ts.add_subparsers(dest="ts_cmd", required=True)

    p_ts_script = ts_sub.add_parser("script", help="Print the parsed script for one .srt file")
    p_ts_script.add_argument("srt_path", type=Path)
    p_ts_script.set_defaults(func=cmd_ts_script)

    p_ts_extract = ts_sub.add_parser("extract", help="Extract episode facts via the Claude API")
    p_ts_extract.add_argument("--root", type=Path, default=Path("pointless_transcripts"))
    p_ts_extract.add_argument("--out", type=Path, default=Path("data/episodes"))
    p_ts_extract.add_argument("--only", action="append", help="Episode id like s34e01 (repeatable)")
    p_ts_extract.add_argument("--limit", type=int)
    p_ts_extract.add_argument("--batch", action="store_true", help="Use the Batch API (50%% cheaper)")
    p_ts_extract.set_defaults(func=cmd_ts_extract)

    p_ts_classify = ts_sub.add_parser(
        "classify", help="Annotate rounds as open-recall vs assisted via the Claude API"
    )
    p_ts_classify.add_argument("--episodes", type=Path, default=Path("data/episodes"))
    p_ts_classify.set_defaults(func=cmd_ts_classify)

    p_ts_merge = ts_sub.add_parser("merge", help="Merge extracted episodes into data/evidence.json")
    p_ts_merge.add_argument("--episodes", type=Path, default=Path("data/episodes"))
    p_ts_merge.add_argument("--out", type=Path, default=Path("data/evidence.json"))
    p_ts_merge.add_argument("--report", type=Path, default=Path("data/evidence_report.json"))
    p_ts_merge.set_defaults(func=cmd_ts_merge)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
