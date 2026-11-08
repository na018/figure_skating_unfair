"""Public API and command-line entry point for ISU result collection."""

from __future__ import annotations

import argparse
from pathlib import Path

from .isu_config import (
    CHALLENGER_EVENTS,
    CHAMPIONSHIP_EVENTS,
    GRAND_PRIX_EVENTS,
    OUTPUT_COLUMNS,
    TARGET_EVENTS,
    ISUEvent,
)
from .isu_results_collector import ISUResultsCollector

__all__ = [
    "CHALLENGER_EVENTS",
    "CHAMPIONSHIP_EVENTS",
    "GRAND_PRIX_EVENTS",
    "ISUEvent",
    "OUTPUT_COLUMNS",
    "TARGET_EVENTS",
    "ISUResultsCollector",
    "main",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download official ISU per-skater judging PDFs, seasonal officials lists, "
            "and parse judge marks."
        )
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="redownload protocol and panel files even when cached files exist",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/judge_marks.csv"),
        help="CSV output path (default: data/processed/judge_marks.csv)",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="directory for original downloaded sources (default: data/raw)",
    )
    parser.add_argument(
        "--officials-list-url",
        action="append",
        default=[],
        metavar="SEASON=URL",
        help=(
            "official officials-list PDF URL for a season not in the built-in source "
            "table; may be supplied more than once"
        ),
    )
    args = parser.parse_args()
    officials_sources: dict[str, str] = {}
    for specification in args.officials_list_url:
        season, separator, url = specification.partition("=")
        if not separator or not season.strip() or not url.strip():
            parser.error("--officials-list-url must use the form SEASON=URL")
        officials_sources[season.strip()] = url.strip()
    frame = ISUResultsCollector(
        raw_dir=args.raw_dir,
        output_path=args.output,
        refresh=args.refresh,
        officials_sources=officials_sources,
    ).collect()
    print(f"Saved {frame.height:,} judge marks to {args.output}")
    unresolved_path = args.output.with_name("judge_federation_unmatched.csv")
    print(f"Unmatched or unavailable judge affiliations are listed in {unresolved_path}")
    print(
        frame.group_by("competition_id", "event_category", "mark_type")
        .len()
        .sort("competition_id", "event_category", "mark_type")
    )


if __name__ == "__main__":
    main()
