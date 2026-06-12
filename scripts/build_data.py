"""Export curated category JSON into docs/data/.

The static app reads only these JSON files at runtime, so this script is the
offline build step for GitHub Pages.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pointless_revision.categories import CATEGORIES  # noqa: E402
from pointless_revision.evidence import write_play_payload  # noqa: E402
from pointless_revision.export import write_static_data  # noqa: E402
from pointless_revision.finals import write_finals_payload  # noqa: E402


DOCS_DATA = ROOT / "docs" / "data"
EPISODES_DIR = ROOT / "data" / "episodes"
FINAL_POOL = ROOT / "data" / "final_pool.json"
FINAL_INFERENCES = ROOT / "data" / "final_pool_inferences.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DOCS_DATA,
        help="Directory for generated static JSON",
    )
    args = parser.parse_args(argv)

    write_static_data(args.out_dir)
    print(f"wrote {len(CATEGORIES)} categories -> {args.out_dir.relative_to(ROOT)}")
    if EPISODES_DIR.exists():
        payload = write_play_payload(EPISODES_DIR, args.out_dir / "episodes.json")
        print(
            f"wrote {payload['n_rounds']} playable rounds from "
            f"{len(payload['episodes'])} episodes -> {args.out_dir.relative_to(ROOT)}/episodes.json"
        )
    if FINAL_POOL.exists():
        finals = write_finals_payload(FINAL_POOL, FINAL_INFERENCES, args.out_dir / "finals.json")
        print(
            f"wrote {finals['n_cards']} in-play final cards -> "
            f"{args.out_dir.relative_to(ROOT)}/finals.json"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
