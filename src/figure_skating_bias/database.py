"""Build a normalized SQLite database from collected ISU judge marks."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE competitions (
    competition_id TEXT PRIMARY KEY,
    competition_name TEXT NOT NULL,
    season TEXT NOT NULL,
    scoring_rule_version TEXT NOT NULL
);

CREATE TABLE event_segments (
    segment_id INTEGER PRIMARY KEY,
    competition_id TEXT NOT NULL REFERENCES competitions(competition_id),
    event_category TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_division TEXT NOT NULL,
    segment TEXT NOT NULL,
    UNIQUE (competition_id, event_category, event_type, event_division, segment)
);

CREATE TABLE entries (
    entry_id TEXT PRIMARY KEY
);

CREATE TABLE performances (
    performance_id INTEGER PRIMARY KEY,
    segment_id INTEGER NOT NULL REFERENCES event_segments(segment_id),
    entry_id TEXT NOT NULL REFERENCES entries(entry_id),
    entry_name TEXT NOT NULL,
    entry_nationality TEXT NOT NULL,
    rank INTEGER,
    UNIQUE (segment_id, entry_id)
);

CREATE TABLE performance_totals (
    performance_id INTEGER PRIMARY KEY REFERENCES performances(performance_id),
    total_segment_score REAL,
    total_element_score REAL,
    program_component_score REAL,
    total_deductions REAL
);

CREATE TABLE judges (
    judge_id TEXT PRIMARY KEY
);

CREATE TABLE judge_assignments (
    assignment_id INTEGER PRIMARY KEY,
    segment_id INTEGER NOT NULL REFERENCES event_segments(segment_id),
    judge_id TEXT NOT NULL REFERENCES judges(judge_id),
    panel_assignment TEXT NOT NULL,
    judge_order INTEGER NOT NULL,
    judge_name TEXT NOT NULL,
    judge_nationality TEXT NOT NULL,
    judge_federation TEXT,
    judge_federation_match TEXT,
    judge_federation_source_url TEXT,
    UNIQUE (segment_id, panel_assignment)
);

CREATE TABLE source_manifests (
    competition_id TEXT PRIMARY KEY REFERENCES competitions(competition_id),
    collected_at_utc TEXT,
    manifest_file TEXT NOT NULL
);

CREATE TABLE source_documents (
    source_id INTEGER PRIMARY KEY,
    competition_id TEXT NOT NULL REFERENCES competitions(competition_id),
    kind TEXT NOT NULL,
    season TEXT,
    status TEXT,
    url TEXT,
    file TEXT,
    sha256 TEXT,
    UNIQUE (competition_id, kind, url, file, sha256)
);

CREATE TABLE marks (
    mark_id INTEGER PRIMARY KEY,
    performance_id INTEGER NOT NULL REFERENCES performances(performance_id),
    assignment_id INTEGER NOT NULL REFERENCES judge_assignments(assignment_id),
    source_id INTEGER NOT NULL REFERENCES source_documents(source_id),
    mark_type TEXT NOT NULL,
    element_number INTEGER,
    element_type TEXT,
    base_value REAL,
    technical_call TEXT,
    goe_total REAL,
    component TEXT,
    component_factor REAL,
    score REAL NOT NULL,
    panel_mean REAL,
    panel_median REAL
);

CREATE INDEX idx_event_segments_lookup
    ON event_segments(event_category, event_type, event_division, segment, competition_id);
CREATE INDEX idx_performances_entry
    ON performances(entry_id, segment_id);
CREATE INDEX idx_performances_name
    ON performances(entry_name);
CREATE INDEX idx_judge_assignments_judge
    ON judge_assignments(judge_id, segment_id);
CREATE INDEX idx_marks_performance
    ON marks(performance_id, mark_type);
CREATE INDEX idx_marks_source
    ON marks(source_id);
CREATE INDEX idx_source_documents_kind
    ON source_documents(competition_id, kind);
"""

CSV_COLUMNS = {
    "competition_id",
    "competition_name",
    "season",
    "scoring_rule_version",
    "event_category",
    "segment",
    "entry_id",
    "entry_name",
    "entry_nationality",
    "rank",
    "total_segment_score",
    "total_element_score",
    "program_component_score",
    "total_deductions",
    "judge_id",
    "judge_panel_assignment",
    "judge_name",
    "judge_nationality",
    "judge_federation",
    "judge_federation_match",
    "judge_federation_source_url",
    "mark_type",
    "element_number",
    "element_type",
    "base_value",
    "technical_call",
    "goe_total",
    "component",
    "component_factor",
    "score",
    "panel_mean",
    "panel_median",
    "source_url",
    "source_file",
    "source_sha256",
}
BATCH_SIZE = 10_000


def _nullable(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    return value


def _nullable_int(value: str | None) -> int | None:
    normalized = _nullable(value)
    return int(normalized) if normalized is not None else None


def _nullable_float(value: str | None) -> float | None:
    normalized = _nullable(value)
    return float(normalized) if normalized is not None else None


def _event_division(source_file: str) -> str:
    filename = Path(source_file).name.upper()
    if "JUNIOR----" in filename:
        return "junior"
    if "ADVNOV----" in filename:
        return "advanced_novice"
    return "senior"


def _load_manifests(
    connection: sqlite3.Connection, raw_dir: Path
) -> dict[tuple[str, str], int]:
    source_ids: dict[tuple[str, str], int] = {}
    manifests = sorted(raw_dir.glob("season*/*/source_manifest.json"))
    if not manifests:
        raise FileNotFoundError(f"No event source manifests found under {raw_dir}")

    for manifest_path in manifests:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        competition_id = manifest["competition_id"]
        connection.execute(
            """
            INSERT INTO source_manifests (competition_id, collected_at_utc, manifest_file)
            VALUES (?, ?, ?)
            """,
            (
                competition_id,
                manifest.get("collected_at_utc"),
                manifest_path.as_posix(),
            ),
        )
        for source in manifest.get("sources", []):
            cursor = connection.execute(
                """
                INSERT INTO source_documents
                    (competition_id, kind, season, status, url, file, sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    competition_id,
                    source["kind"],
                    source.get("season"),
                    source.get("status"),
                    source.get("url"),
                    source.get("file"),
                    source.get("sha256"),
                ),
            )
            sha256 = source.get("sha256")
            if sha256:
                source_ids[(competition_id, sha256)] = cursor.lastrowid
    return source_ids


def _build_database(csv_path: Path, raw_dir: Path, database_path: Path) -> int:
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.executescript(SCHEMA)
        competition_metadata: dict[str, tuple[str, str, str]] = {}
        with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            missing_columns = CSV_COLUMNS - set(reader.fieldnames or [])
            if missing_columns:
                raise ValueError(f"CSV is missing required columns: {sorted(missing_columns)}")
            for row in reader:
                competition_id = row["competition_id"]
                metadata = (
                    row["competition_name"],
                    row["season"],
                    row["scoring_rule_version"],
                )
                previous = competition_metadata.setdefault(competition_id, metadata)
                if previous != metadata:
                    raise ValueError(f"Inconsistent competition metadata for {competition_id}")
                connection.execute(
                    """
                    INSERT OR IGNORE INTO competitions
                        (competition_id, competition_name, season, scoring_rule_version)
                    VALUES (?, ?, ?, ?)
                    """,
                    (competition_id, *metadata),
                )
        if not competition_metadata:
            raise ValueError(f"No judge marks found in {csv_path}")

        source_ids = _load_manifests(connection, raw_dir)
        segments: dict[tuple[str, str, str], int] = {}
        performances: dict[tuple[int, str], int] = {}
        assignments: dict[tuple[int, str], int] = {}
        mark_batch: list[tuple[Any, ...]] = []
        row_count = 0

        with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                competition_id = row["competition_id"]

                segment_key = (
                    competition_id,
                    row["event_category"],
                    row.get("event_type") or "individual_event",
                    _event_division(row["source_file"]),
                    row["segment"],
                )
                segment_id = segments.get(segment_key)
                if segment_id is None:
                    cursor = connection.execute(
                        """
                        INSERT INTO event_segments
                            (competition_id, event_category, event_type, event_division, segment)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        segment_key,
                    )
                    segment_id = cursor.lastrowid
                    segments[segment_key] = segment_id

                entry_id = row["entry_id"]
                connection.execute(
                    "INSERT OR IGNORE INTO entries (entry_id) VALUES (?)",
                    (entry_id,),
                )
                performance_key = (segment_id, entry_id)
                performance_id = performances.get(performance_key)
                if performance_id is None:
                    cursor = connection.execute(
                        """
                        INSERT INTO performances
                            (segment_id, entry_id, entry_name, entry_nationality, rank)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            segment_id,
                            entry_id,
                            row["entry_name"],
                            row["entry_nationality"],
                            _nullable_int(row["rank"]),
                        ),
                    )
                    performance_id = cursor.lastrowid
                    performances[performance_key] = performance_id

                connection.execute(
                    """
                    INSERT OR IGNORE INTO performance_totals (
                        performance_id, total_segment_score, total_element_score,
                        program_component_score, total_deductions
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        performance_id,
                        _nullable_float(row["total_segment_score"]),
                        _nullable_float(row["total_element_score"]),
                        _nullable_float(row["program_component_score"]),
                        _nullable_float(row["total_deductions"]),
                    ),
                )

                judge_id = row["judge_id"]
                connection.execute(
                    "INSERT OR IGNORE INTO judges (judge_id) VALUES (?)",
                    (judge_id,),
                )
                panel_assignment = row["judge_panel_assignment"]
                assignment_key = (segment_id, panel_assignment)
                assignment_id = assignments.get(assignment_key)
                if assignment_id is None:
                    cursor = connection.execute(
                        """
                        INSERT INTO judge_assignments (
                            segment_id, judge_id, panel_assignment, judge_order, judge_name,
                            judge_nationality, judge_federation, judge_federation_match,
                            judge_federation_source_url
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            segment_id,
                            judge_id,
                            panel_assignment,
                            _nullable_int(
                                panel_assignment.rsplit(":", maxsplit=1)[-1].removeprefix("J")
                            ),
                            row["judge_name"],
                            row["judge_nationality"],
                            _nullable(row["judge_federation"]),
                            _nullable(row["judge_federation_match"]),
                            _nullable(row["judge_federation_source_url"]),
                        ),
                    )
                    assignment_id = cursor.lastrowid
                    assignments[assignment_key] = assignment_id
                elif connection.execute(
                    "SELECT judge_id FROM judge_assignments WHERE assignment_id = ?",
                    (assignment_id,),
                ).fetchone()[0] != judge_id:
                    raise ValueError(
                        f"Conflicting judge identity for {competition_id} "
                        f"{row['event_category']} {row['segment']} {panel_assignment}"
                    )

                source_id = source_ids.get((competition_id, row["source_sha256"]))
                if source_id is None:
                    raise ValueError(
                        f"No source-manifest record for {competition_id} "
                        f"with SHA-256 {row['source_sha256']}"
                    )
                mark_batch.append(
                    (
                        performance_id,
                        assignment_id,
                        source_id,
                        row["mark_type"],
                        _nullable_int(row["element_number"]),
                        _nullable(row["element_type"]),
                        _nullable_float(row["base_value"]),
                        _nullable(row["technical_call"]),
                        _nullable_float(row["goe_total"]),
                        _nullable(row["component"]),
                        _nullable_float(row["component_factor"]),
                        float(row["score"]),
                        _nullable_float(row["panel_mean"]),
                        _nullable_float(row["panel_median"]),
                    )
                )
                row_count += 1
                if len(mark_batch) >= BATCH_SIZE:
                    _insert_marks(connection, mark_batch)
                    mark_batch.clear()

        if mark_batch:
            _insert_marks(connection, mark_batch)
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise sqlite3.IntegrityError(f"Foreign-key violations found: {violations[:5]}")
        connection.commit()
        return row_count
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _insert_marks(connection: sqlite3.Connection, batch: list[tuple[Any, ...]]) -> None:
    connection.executemany(
        """
        INSERT INTO marks (
            performance_id, assignment_id, source_id, mark_type, element_number,
            element_type, base_value, technical_call, goe_total, component,
            component_factor, score, panel_mean, panel_median
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        batch,
    )


def build_database(
    csv_path: Path,
    raw_dir: Path,
    database_path: Path,
) -> int:
    """Build the SQLite database atomically and return the imported mark count."""
    csv_path = Path(csv_path)
    raw_dir = Path(raw_dir)
    database_path = Path(database_path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Judge marks CSV not found: {csv_path}")
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        prefix=f".{database_path.name}.",
        suffix=".tmp",
        dir=database_path.parent,
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
    try:
        row_count = _build_database(csv_path, raw_dir, temporary_path)
        os.replace(temporary_path, database_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return row_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a normalized SQLite database from collected ISU judge marks."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("data/processed/judge_marks.csv"),
        help="normalized judge-marks CSV (default: data/processed/judge_marks.csv)",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="source-manifest directory (default: data/raw)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/figure_skating.sqlite3"),
        help="SQLite output path (default: data/processed/figure_skating.sqlite3)",
    )
    args = parser.parse_args()
    row_count = build_database(args.csv, args.raw_dir, args.output)
    print(f"Built {args.output} with {row_count:,} individual judge marks.")


if __name__ == "__main__":
    main()
