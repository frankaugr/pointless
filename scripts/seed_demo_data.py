"""Compatibility wrapper for older setup notes.

The app now uses curated offline fixtures, so "seeding" is just a static JSON
export.
"""

from __future__ import annotations

from build_data import main


if __name__ == "__main__":
    raise SystemExit(main())
