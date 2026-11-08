import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from figure_skating_bias.database import build_database
from figure_skating_bias.site_export import export_site_data


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.csv_path = self.root / "judge_marks.csv"
        self.raw_dir = self.root / "raw"
        event_dir = self.raw_dir / "season2526" / "test-event"
        event_dir.mkdir(parents=True)
        self.database_path = self.root / "figure_skating.sqlite3"

        self.source_sha256 = "a" * 64
        self.junior_source_sha256 = "b" * 64
        manifest = {
            "competition_id": "test-event",
            "collected_at_utc": "2026-01-01T00:00:00+00:00",
            "sources": [
                {
                    "kind": "judge_scores_pdf",
                    "url": "https://results.isu.org/test.pdf",
                    "file": "data/raw/season2526/test-event/test.pdf",
                    "sha256": self.source_sha256,
                },
                {
                    "kind": "judge_scores_pdf",
                    "url": "https://results.isu.org/junior-test.pdf",
                    "file": (
                        "data/raw/season2526/test-event/"
                        "FSKMSINGLES-JUNIOR----QUAL000100--_JudgesDetailsperSkater.pdf"
                    ),
                    "sha256": self.junior_source_sha256,
                },
            ],
        }
        (event_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        self.columns = [
            "competition_id",
            "competition_name",
            "season",
            "scoring_rule_version",
            "event_category",
            "event_type",
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
        ]
        self.rows = [
            self._row(mark_type="GOE", element_number="1", score="2.0"),
            self._row(mark_type="PCS", component="Skating Skills", score="9.0"),
        ]
        self._write_csv()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _row(
        self,
        *,
        mark_type: str,
        score: str,
        element_number: str = "",
        component: str = "",
    ) -> dict[str, str]:
        values = {
            "competition_id": "test-event",
            "competition_name": "Test Figure Skating Event",
            "season": "season2526",
            "scoring_rule_version": "season2526",
            "event_category": "men_singles",
            "event_type": "individual_event",
            "segment": "free_skating",
            "entry_id": "test-skater-usa",
            "entry_name": "Test Skater",
            "entry_nationality": "USA",
            "rank": "1",
            "total_segment_score": "10.0",
            "total_element_score": "8.0",
            "program_component_score": "2.0",
            "total_deductions": "0.0",
            "judge_id": "test-judge",
            "judge_panel_assignment": "J1",
            "judge_name": "Example Judge",
            "judge_nationality": "USA",
            "judge_federation": "",
            "judge_federation_match": "unmatched",
            "judge_federation_source_url": "",
            "mark_type": mark_type,
            "element_number": element_number,
            "element_type": "3A" if mark_type == "GOE" else "",
            "base_value": "8.0" if mark_type == "GOE" else "",
            "technical_call": "",
            "goe_total": "2.0" if mark_type == "GOE" else "",
            "component": component,
            "component_factor": "1.0" if component else "",
            "score": score,
            "panel_mean": score,
            "panel_median": score,
            "source_url": "https://results.isu.org/test.pdf",
            "source_file": "data/raw/season2526/test-event/test.pdf",
            "source_sha256": self.source_sha256,
        }
        return values

    def _write_csv(self) -> None:
        with self.csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.columns)
            writer.writeheader()
            writer.writerows(self.rows)

    def test_builds_normalized_database_and_preserves_unknown_affiliation(self) -> None:
        imported = build_database(self.csv_path, self.raw_dir, self.database_path)

        self.assertEqual(imported, 2)
        with sqlite3.connect(self.database_path) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM marks").fetchone()[0],
                2,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM performances").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute(
                    """
                    SELECT total_segment_score, total_element_score,
                           program_component_score, total_deductions
                    FROM performance_totals
                    """
                ).fetchone(),
                (10.0, 8.0, 2.0, 0.0),
            )
            self.assertEqual(
                connection.execute(
                    """
                    SELECT judge_federation, judge_federation_match
                    FROM judge_assignments
                    """
                ).fetchone(),
                (None, "unmatched"),
            )
            self.assertEqual(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM marks m
                    JOIN source_documents s ON s.source_id = m.source_id
                    WHERE s.sha256 = ?
                    """,
                    (self.source_sha256,),
                ).fetchone()[0],
                2,
            )
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_missing_source_manifest_record_does_not_replace_existing_database(self) -> None:
        self.database_path.write_bytes(b"existing database")
        self.rows[0]["source_sha256"] = "c" * 64
        self._write_csv()

        with self.assertRaisesRegex(ValueError, "No source-manifest record"):
            build_database(self.csv_path, self.raw_dir, self.database_path)

        self.assertEqual(self.database_path.read_bytes(), b"existing database")

    def test_keeps_junior_and_senior_segments_separate(self) -> None:
        junior_row = self._row(mark_type="GOE", element_number="1", score="2.0")
        junior_row["source_sha256"] = self.junior_source_sha256
        junior_row["source_file"] = (
            "data/raw/season2526/test-event/"
            "FSKMSINGLES-JUNIOR----QUAL000100--_JudgesDetailsperSkater.pdf"
        )
        self.rows.append(junior_row)
        self._write_csv()

        build_database(self.csv_path, self.raw_dir, self.database_path)

        with sqlite3.connect(self.database_path) as connection:
            divisions = connection.execute(
                "SELECT event_division FROM event_segments ORDER BY event_division"
            ).fetchall()
            self.assertEqual(divisions, [("junior",), ("senior",)])
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM marks").fetchone()[0], 3)

    def test_exports_search_index_and_performance_json(self) -> None:
        build_database(self.csv_path, self.raw_dir, self.database_path)
        output_dir = self.root / "site-data"
        portraits_path = self.root / "portraits.json"
        portraits_path.write_text(
            json.dumps(
                {
                    "test-skater-usa": {
                        "url": "https://images.example.org/test-skater.jpg",
                        "source_url": "https://commons.wikimedia.org/wiki/File:Test.jpg",
                        "title": "Test skating photo",
                        "creator": "Example Photographer",
                        "license": "CC BY 4.0",
                        "license_url": "https://creativecommons.org/licenses/by/4.0/",
                    }
                }
            ),
            encoding="utf-8",
        )

        entry_count = export_site_data(self.database_path, output_dir, portraits_path)

        self.assertEqual(entry_count, 1)
        index = json.loads((output_dir / "index.json").read_text(encoding="utf-8"))
        detail_path = output_dir / index[0]["file"]
        details = json.loads(detail_path.read_text(encoding="utf-8"))
        self.assertEqual(index[0]["name"], "Test Skater")
        self.assertEqual(
            index[0]["portrait_url"],
            "https://images.example.org/test-skater.jpg",
        )
        self.assertEqual(index[0]["portrait_credit"]["creator"], "Example Photographer")
        self.assertEqual(details["portrait_url"], index[0]["portrait_url"])
        self.assertEqual(details["portrait_credit"], index[0]["portrait_credit"])
        self.assertEqual(len(details["performances"]), 1)
        self.assertEqual(details["performances"][0]["total_segment_score"], 10.0)
        self.assertEqual(details["performances"][0]["total_element_score"], 8.0)
        self.assertEqual(details["performances"][0]["program_component_score"], 2.0)
        self.assertEqual(len(details["performances"][0]["elements"]), 1)
        self.assertEqual(len(details["performances"][0]["components"]), 1)
        self.assertEqual(
            details["performances"][0]["elements"][0]["judge_scores"],
            [2.0],
        )


if __name__ == "__main__":
    unittest.main()
