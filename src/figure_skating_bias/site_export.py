"""Export the local SQLite dataset as files for a static GitHub Pages site."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _slug(entry_id: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", entry_id.casefold()).strip("-")


def export_site_data(
    database_path: Path,
    output_dir: Path,
    portraits_path: Path | None = None,
) -> int:
    """Write a small entry index and one detailed JSON file per searchable entry."""
    database_path = Path(database_path)
    output_dir = Path(output_dir)
    if not database_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {database_path}")
    portraits: dict[str, dict[str, str]] = {}
    if portraits_path is not None:
        portraits_path = Path(portraits_path)
        portrait_data = json.loads(portraits_path.read_text(encoding="utf-8"))
        if not isinstance(portrait_data, dict):
            raise ValueError("Portrait mapping must be a JSON object keyed by entry ID.")
        required_fields = {
            "url",
            "source_url",
            "title",
            "creator",
            "license",
            "license_url",
        }
        for entry_id, portrait in portrait_data.items():
            if (
                not isinstance(entry_id, str)
                or not isinstance(portrait, dict)
                or not required_fields.issubset(portrait)
                or not all(
                    isinstance(portrait[field], str) and portrait[field].strip()
                    for field in required_fields
                )
            ):
                raise ValueError(
                    "Each portrait must include url, source_url, title, creator, "
                    f"license, and license_url: {entry_id}"
                )
            for field in ("url", "source_url", "license_url"):
                if urlparse(portrait[field]).scheme != "https":
                    raise ValueError(
                        f"Portrait {field} must use HTTPS: {entry_id}"
                    )
        portraits = portrait_data
    output_dir.mkdir(parents=True, exist_ok=True)
    skater_dir = output_dir / "skaters"
    skater_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(f"file:{database_path.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        competitions = [
            dict(row)
            for row in connection.execute(
                """
                SELECT competition_id, competition_name, season
                FROM competitions
                ORDER BY season DESC, competition_name
                """
            )
        ]
        known_entry_ids = {
            row[0] for row in connection.execute("SELECT entry_id FROM entries")
        }
        unknown_portraits = set(portraits) - known_entry_ids
        if unknown_portraits:
            raise ValueError(
                "Portrait mapping contains unknown entry IDs: "
                f"{sorted(unknown_portraits)[:5]}"
            )
        metadata = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "competition_count": len(competitions),
            "mark_count": connection.execute("SELECT COUNT(*) FROM marks").fetchone()[0],
        }
        entries: list[dict[str, Any]] = []
        current_entry_id: str | None = None
        current_entry: dict[str, Any] | None = None
        current_performance_id: int | None = None
        current_performance: dict[str, Any] | None = None
        judge_slots: dict[int, dict[str, Any]] = {}
        grouped_marks: dict[tuple[str, int | None, str | None], dict[str, Any]] = {}
        entry_slugs: set[str] = set()

        query = """
            SELECT
                e.entry_id,
                p.performance_id,
                p.entry_name,
                p.entry_nationality,
                p.rank,
                pt.total_segment_score,
                pt.total_element_score,
                pt.program_component_score,
                pt.total_deductions,
                c.competition_id,
                c.competition_name,
                c.season,
                es.event_category,
                es.event_type,
                es.event_division,
                es.segment,
                ja.judge_order,
                ja.judge_name,
                ja.judge_nationality,
                ja.judge_federation,
                m.mark_type,
                m.element_number,
                m.element_type,
                m.base_value,
                m.technical_call,
                m.goe_total,
                m.component,
                m.component_factor,
                m.score,
                m.panel_mean,
                m.panel_median,
                sd.url AS source_url
            FROM marks m
            JOIN performances p ON p.performance_id = m.performance_id
            LEFT JOIN performance_totals pt ON pt.performance_id = p.performance_id
            JOIN entries e ON e.entry_id = p.entry_id
            JOIN event_segments es ON es.segment_id = p.segment_id
            JOIN competitions c ON c.competition_id = es.competition_id
            JOIN judge_assignments ja ON ja.assignment_id = m.assignment_id
            JOIN source_documents sd ON sd.source_id = m.source_id
            ORDER BY
                e.entry_id,
                p.performance_id,
                ja.judge_order,
                m.mark_type,
                m.element_number,
                m.component
        """

        def finish_performance() -> None:
            if current_performance is None or current_performance.get("_finalized"):
                return
            current_performance["judge_panel"] = [
                judge_slots[slot] for slot in sorted(judge_slots)
            ]
            for mark in grouped_marks.values():
                mark["judge_scores"] = [
                    mark["_scores"].get(slot)
                    for slot in sorted(judge_slots)
                ]
                del mark["_scores"]
            current_performance["elements"] = [
                mark
                for mark in grouped_marks.values()
                if mark["mark_type"] == "GOE"
            ]
            current_performance["components"] = [
                mark
                for mark in grouped_marks.values()
                if mark["mark_type"] == "PCS"
            ]
            current_performance["_finalized"] = True
            current_entry["performances"].append(current_performance)

        def finish_entry() -> None:
            if current_entry is None:
                return
            file_name = f"{current_entry['file_key']}.json"
            output_entry = {
                key: value for key, value in current_entry.items() if key != "file_key"
            }
            _json_write(skater_dir / file_name, output_entry)
            entries.append(current_entry)

        for row in connection.execute(query):
            entry_id = row["entry_id"]
            if entry_id != current_entry_id:
                finish_performance()
                finish_entry()
                slug = _slug(entry_id)
                if not slug or slug in entry_slugs:
                    slug = f"{slug or 'entry'}-{len(entry_slugs) + 1}"
                entry_slugs.add(slug)
                current_entry_id = entry_id
                portrait = portraits.get(entry_id)
                current_entry = {
                    "entry_id": entry_id,
                    "name": row["entry_name"],
                    "nationality": row["entry_nationality"],
                    "portrait_url": portrait["url"] if portrait else None,
                    "portrait_credit": (
                        {
                            "source_url": portrait["source_url"],
                            "title": portrait["title"],
                            "creator": portrait["creator"],
                            "license": portrait["license"],
                            "license_url": portrait["license_url"],
                        }
                        if portrait
                        else None
                    ),
                    "performances": [],
                    "file_key": slug,
                }
                current_performance_id = None

            if row["performance_id"] != current_performance_id:
                finish_performance()
                current_performance_id = row["performance_id"]
                current_performance = {
                    "competition_id": row["competition_id"],
                    "competition_name": row["competition_name"],
                    "season": row["season"],
                    "event_category": row["event_category"],
                    "event_type": row["event_type"],
                    "event_division": row["event_division"],
                    "segment": row["segment"],
                    "rank": row["rank"],
                    "total_segment_score": row["total_segment_score"],
                    "total_element_score": row["total_element_score"],
                    "program_component_score": row["program_component_score"],
                    "total_deductions": row["total_deductions"],
                    "source_url": row["source_url"],
                    "judge_panel": [],
                    "elements": [],
                    "components": [],
                }
                judge_slots = {}
                grouped_marks = {}

            slot = int(row["judge_order"])
            judge_slots[slot] = {
                "number": slot,
                "name": row["judge_name"],
                "nationality": row["judge_nationality"],
                "federation": row["judge_federation"],
            }
            mark_key = (
                row["mark_type"],
                row["element_number"],
                row["component"],
            )
            mark = grouped_marks.get(mark_key)
            if mark is None:
                mark = {
                    "mark_type": row["mark_type"],
                    "element_number": row["element_number"],
                    "element_type": row["element_type"],
                    "base_value": row["base_value"],
                    "technical_call": row["technical_call"],
                    "goe_total": row["goe_total"],
                    "component": row["component"],
                    "component_factor": row["component_factor"],
                    "panel_mean": row["panel_mean"],
                    "panel_median": row["panel_median"],
                    "_scores": {},
                }
                grouped_marks[mark_key] = mark
            mark["_scores"][slot] = row["score"]

        finish_performance()
        finish_entry()
        entries.sort(key=lambda entry: (entry["name"].casefold(), entry["nationality"]))
        index_entries = []
        for entry in entries:
            performances = entry["performances"]
            index_entries.append(
                {
                    "entry_id": entry["entry_id"],
                    "name": entry["name"],
                    "nationality": entry["nationality"],
                    "portrait_url": entry["portrait_url"],
                    "portrait_credit": entry["portrait_credit"],
                    "file": f"skaters/{entry['file_key']}.json",
                    "performance_count": len(performances),
                    "competitions": sorted(
                        {performance["competition_id"] for performance in performances}
                    ),
                    "event_categories": sorted(
                        {performance["event_category"] for performance in performances}
                    ),
                }
            )
        _json_write(output_dir / "index.json", index_entries)
        _json_write(
            output_dir / "site.json",
            {**metadata, "entry_count": len(entries), "competitions": competitions},
        )
        return len(entries)
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the local SQLite database into static GitHub Pages JSON."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/processed/figure_skating.sqlite3"),
        help="SQLite database path (default: data/processed/figure_skating.sqlite3)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/data"),
        help="static JSON output directory (default: docs/data)",
    )
    parser.add_argument(
        "--portraits",
        type=Path,
        default=Path("data/portraits.json"),
        help="JSON map from entry IDs to portraits with source and license attribution",
    )
    args = parser.parse_args()
    count = export_site_data(args.database, args.output, args.portraits)
    print(f"Exported {count:,} skater/team entries to {args.output}")


if __name__ == "__main__":
    main()
