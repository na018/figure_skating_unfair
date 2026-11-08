"""Orchestrate ISU source collection, parsing, and dataset output."""

from __future__ import annotations

import json
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import polars as pl

from .isu_config import OUTPUT_COLUMNS, TARGET_EVENTS, ISUEvent
from .isu_officials import OFFICIALS_LIST_URLS, _officials_roster
from .isu_protocol import _parse_protocol
from .isu_sources import (
    _download,
    _judge_panel,
    _official_sources,
    _sha256,
)


class ISUResultsCollector:
    """Fetch official ISU protocol PDFs and create a normalized judge-mark dataset.

    Existing source files are reused by default. Pass ``refresh=True`` to download
    current copies again. The collector stores original files and a SHA-256 manifest
    under ``data/raw/``; parsed output is written separately.
    """

    def __init__(
        self,
        raw_dir: Path = Path("data/raw"),
        output_path: Path = Path("data/processed/judge_marks.csv"),
        *,
        refresh: bool = False,
        delay_seconds: float = 0.2,
        officials_sources: dict[str, str | None] | None = None,
    ) -> None:
        self.raw_dir = raw_dir
        self.output_path = output_path
        self.refresh = refresh
        self.delay_seconds = delay_seconds
        self.officials_sources = dict(OFFICIALS_LIST_URLS)
        if officials_sources:
            self.officials_sources.update(officials_sources)
        self._officials_cache: dict[
            str, tuple[dict[str, set[str]] | None, str | None, Path | None, str | None]
        ] = {}

    def _seasonal_officials(
        self, season: str
    ) -> tuple[dict[str, set[str]] | None, str | None, Path | None, str | None]:
        if season in self._officials_cache:
            return self._officials_cache[season]

        source_url = self.officials_sources.get(season)
        if source_url is None:
            warnings.warn(
                f"No verified ISU officials list is configured for {season}; "
                "judge federations will remain unknown for this season.",
                RuntimeWarning,
                stacklevel=2,
            )
            result = (None, None, None, None)
            self._officials_cache[season] = result
            return result

        source_path = self.raw_dir / season / "officials_list.pdf"
        content = _download(source_url, source_path, self.refresh, self.delay_seconds)
        if not content.startswith(b"%PDF"):
            raise ValueError(f"Official officials-list link did not return a PDF: {source_url}")
        roster = _officials_roster(content, source_url)
        result = (roster, source_url, source_path, _sha256(content))
        self._officials_cache[season] = result
        return result

    def collect_event(self, event: ISUEvent) -> list[dict[str, object]]:
        event_dir = self.raw_dir / event.season / event.event_code
        index_path = event_dir / "index.htm"
        index_bytes = _download(
            event.index_url,
            index_path,
            self.refresh,
            self.delay_seconds,
            event.trusted_hosts,
        )
        index_html = index_bytes.decode("utf-8", errors="replace")
        sources = _official_sources(event.index_url, index_html)
        officials_roster, officials_url, officials_path, officials_hash = self._seasonal_officials(
            event.season
        )
        rows: list[dict[str, object]] = []
        manifest: list[dict[str, str]] = [
            {
                "kind": "event_index",
                "url": event.index_url,
                "file": str(index_path),
                "sha256": _sha256(index_bytes),
            }
        ]
        if officials_url and officials_path and officials_hash:
            manifest.append(
                {
                    "kind": "seasonal_officials_list",
                    "url": officials_url,
                    "file": str(officials_path),
                    "sha256": officials_hash,
                }
            )
        else:
            manifest.append(
                {
                    "kind": "seasonal_officials_list",
                    "season": event.season,
                    "status": "source_unavailable",
                }
            )

        for pdf_url, panel_url, category in sources:
            pdf_name = Path(urlparse(pdf_url).path).name
            segment_match = re.search(r"(SEG\d+)OF\.htm$", panel_url, re.IGNORECASE)
            if segment_match is None:
                raise ValueError(f"Invalid official panel URL: {panel_url}")
            panel_path = event_dir / f"{segment_match.group(1).upper()}OF.htm"
            panel_bytes = _download(
                panel_url,
                panel_path,
                self.refresh,
                self.delay_seconds,
                event.trusted_hosts,
            )
            panel = _judge_panel(panel_bytes.decode("utf-8", errors="replace"), panel_url)

            pdf_path = event_dir / pdf_name
            pdf_bytes = _download(
                pdf_url,
                pdf_path,
                self.refresh,
                self.delay_seconds,
                event.trusted_hosts,
            )
            if not pdf_bytes.startswith(b"%PDF"):
                raise ValueError(f"Official protocol link did not return a PDF: {pdf_url}")
            pdf_hash = _sha256(pdf_bytes)
            rows.extend(
                _parse_protocol(
                    pdf_bytes,
                    pdf_url,
                    str(pdf_path),
                    pdf_hash,
                    event,
                    category,
                    panel,
                    officials_roster,
                    officials_url,
                )
            )
            manifest.extend(
                [
                    {
                        "kind": "judge_panel",
                        "url": panel_url,
                        "file": str(panel_path),
                        "sha256": _sha256(panel_bytes),
                    },
                    {
                        "kind": "judge_scores_pdf",
                        "url": pdf_url,
                        "file": str(pdf_path),
                        "sha256": pdf_hash,
                    },
                ]
            )

        if not rows:
            raise ValueError(f"No supported discipline marks found for {event.competition_id}")
        manifest_path = event_dir / "source_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "competition_id": event.competition_id,
                    "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                    "sources": manifest,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return rows

    def collect(self, events: Iterable[ISUEvent] = TARGET_EVENTS) -> pl.DataFrame:
        rows = [row for event in events for row in self.collect_event(event)]
        if not rows:
            raise ValueError("No protocol data collected.")
        frame = pl.DataFrame(
            rows,
            schema_overrides={
                "judge_federation": pl.String,
                "judge_federation_match": pl.String,
                "judge_federation_source_url": pl.String,
            },
        ).select(OUTPUT_COLUMNS)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        frame.write_csv(self.output_path)
        unresolved = (
            frame.filter(pl.col("judge_federation_match") != "exact")
            .select(
                "competition_id",
                "season",
                "judge_id",
                "judge_name",
                "judge_nationality",
                "judge_federation_match",
                "judge_federation_source_url",
            )
            .unique()
            .sort("competition_id", "judge_name")
        )
        unresolved_path = self.output_path.with_name("judge_federation_unmatched.csv")
        unresolved.write_csv(unresolved_path)
        if unresolved.height:
            warnings.warn(
                f"{unresolved.height} judge affiliations could not be matched exactly; "
                f"see {unresolved_path}.",
                RuntimeWarning,
                stacklevel=2,
            )
        return frame
