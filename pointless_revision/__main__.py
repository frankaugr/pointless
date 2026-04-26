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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
