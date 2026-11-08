import unittest

import pymupdf

from figure_skating_bias.collectors.isu_config import (
    CHALLENGER_EVENTS,
    GRAND_PRIX_EVENTS,
    TARGET_EVENTS,
    ISUEvent,
)
from figure_skating_bias.collectors.isu_officials import (
    _judge_federation,
    _officials_roster,
)
from figure_skating_bias.collectors.isu_protocol import (
    _element_column_positions,
    _element_row,
    _entry_identity,
    _lines,
    _parse_protocol,
)
from figure_skating_bias.collectors.isu_sources import (
    _judge_panel,
    _official_sources,
    _validate_official_url,
)


class ISUCollectorTests(unittest.TestCase):
    def test_supported_grand_prix_events_are_in_target_collection(self) -> None:
        grand_prix_ids = [event.competition_id for event in GRAND_PRIX_EVENTS]
        target_ids = {event.competition_id for event in TARGET_EVENTS}

        self.assertEqual(len(grand_prix_ids), 31)
        self.assertEqual(len(grand_prix_ids), len(set(grand_prix_ids)))
        self.assertTrue(set(grand_prix_ids).issubset(target_ids))
        self.assertNotIn("gpjpn2021", target_ids)
        self.assertNotIn("gpjpn2022", target_ids)
        self.assertNotIn("gpjpn2023", target_ids)

    def test_supported_challenger_events_have_explicit_official_sources(self) -> None:
        challenger_ids = {event.competition_id for event in CHALLENGER_EVENTS}
        target_ids = {event.competition_id for event in TARGET_EVENTS}

        self.assertEqual(len(challenger_ids), 23)
        self.assertTrue(challenger_ids.issubset(target_ids))
        self.assertTrue(all(event.source_index_url for event in CHALLENGER_EVENTS))
        self.assertTrue(all(event.trusted_hosts for event in CHALLENGER_EVENTS))

    def test_external_event_hosts_are_explicit_and_https_only(self) -> None:
        event = ISUEvent(
            "test-external",
            "Test external event",
            "season2526",
            "test-external",
            "https://results.example.org/index.htm",
            ("results.example.org",),
        )

        self.assertEqual(event.index_url, "https://results.example.org/index.htm")
        _validate_official_url(event.index_url, event.trusted_hosts)
        with self.assertRaises(ValueError):
            _validate_official_url("http://results.example.org/index.htm", event.trusted_hosts)
        with self.assertRaises(ValueError):
            _validate_official_url("https://other.example.org/index.htm", event.trusted_hosts)

    def test_entry_identity_normalizes_name_order_and_diacritics(self) -> None:
        self.assertEqual(
            _entry_identity("Shoma UNO", "JPN"),
            _entry_identity("UNO Shoma", "JPN"),
        )
        self.assertEqual(
            _entry_identity("Léa HÉRITIER", "FRA"),
            _entry_identity("Heritier Lea", "FRA"),
        )

    def test_discovers_individual_and_team_event_pdfs(self) -> None:
        index_url = "https://results.isu.org/results/season2526/owg2026/index.htm"
        html = """
        <a href="SEG001OF.htm">Officials</a>
        <a href="SEG001.htm">Men Short</a>
        <a href="FSKMSINGLES-----------QUAL000100--_JudgesDetailsperSkater.pdf">
          Judges Scores
        </a>
        <a href="SEG009.htm">Team Event</a>
        <a href="FSKXTEAM--------------QUAL0001MN--_JudgesDetailsperSkater.pdf">
          Team Scores
        </a>
        """

        sources = _official_sources(index_url, html)

        self.assertEqual(len(sources), 2)
        self.assertEqual(
            sources[0],
            (
                "https://results.isu.org/results/season2526/owg2026/"
                "FSKMSINGLES-----------QUAL000100--_JudgesDetailsperSkater.pdf",
                "https://results.isu.org/results/season2526/owg2026/SEG001OF.htm",
                "men_singles",
            ),
        )
        self.assertEqual(
            sources[1],
            (
                "https://results.isu.org/results/season2526/owg2026/"
                "FSKXTEAM--------------QUAL0001MN--_JudgesDetailsperSkater.pdf",
                "https://results.isu.org/results/season2526/owg2026/SEG009OF.htm",
                "men_singles",
            ),
        )

    def test_discovers_olympic_team_event_protocols(self) -> None:
        index_url = "https://results.isu.org/results/season2526/owg2026/index.htm"
        html = """
        <a href="SEG009.htm">Men Team Short Program</a>
        <a href="FSKXTEAM--------------QUAL0001MN--_JudgesDetailsperSkater.pdf">
          Judges Scores
        </a>
        <a href="SEG010.htm">Men Team Free Skating</a>
        <a href="FSKXTEAM--------------FNL-0001MN--_JudgesDetailsperSkater.pdf">
          Judges Scores
        </a>
        """

        sources = _official_sources(index_url, html)

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0][2], "men_singles")
        self.assertEqual(sources[1][2], "men_singles")
        self.assertTrue(sources[0][0].endswith("QUAL0001MN--_JudgesDetailsperSkater.pdf"))
        self.assertTrue(sources[1][0].endswith("FNL-0001MN--_JudgesDetailsperSkater.pdf"))

    def test_parses_nested_official_judge_panel(self) -> None:
        html = """
        <table>
          <tr>
            <td>Judge No.1</td><td>Ms. Example Judge</td>
            <td><table><tr><td><img></td><td></td><td>USA</td></tr></table></td>
          </tr>
        </table>
        """

        panel = _judge_panel(html, "https://results.isu.org/example/SEG001OF.htm")

        self.assertEqual(panel, {1: ("Ms. Example Judge", "USA")})

    def test_parses_judges_and_referees_from_seasonal_officials_list(self) -> None:
        document = pymupdf.open()
        page = document.new_page(width=595, height=842)
        lines = [
            "USA - United States of America",
            "ISU Judge",
            "Example Judge, Ms.",
            "ISU Referee",
            "Example Referee, Mr.",
            "ISU Technical Specialist",
            "Ignored Official, Mr.",
            "CAN - Canada",
            "International Judge",
            "Another Official, Ms.",
        ]
        for index, line in enumerate(lines):
            page.insert_text((50, 50 + index * 20), line)
        content = document.tobytes()
        document.close()

        roster = _officials_roster(
            content, "https://isu-d8g8b4b7ece7aphs.a03.azurefd.net/officials.pdf"
        )

        self.assertEqual(roster["EXAMPLE_JUDGE"], {"USA"})
        self.assertEqual(roster["EXAMPLE_REFEREE"], {"USA"})
        self.assertEqual(roster["ANOTHER_OFFICIAL"], {"CAN"})
        self.assertNotIn("IGNORED_OFFICIAL", roster)

    def test_only_exact_unique_officials_matches_receive_a_federation(self) -> None:
        roster = {
            "EXAMPLE_JUDGE": {"USA"},
            "AMBIGUOUS_JUDGE": {"USA", "CAN"},
        }

        self.assertEqual(_judge_federation("Ms. Example Judge", roster), ("USA", "exact"))
        self.assertEqual(_judge_federation("Ambiguous Judge", roster), (None, "ambiguous"))
        self.assertEqual(_judge_federation("Unknown Judge", roster), (None, "unmatched"))
        self.assertEqual(_judge_federation("Unknown Judge", None), (None, "source_unavailable"))

    def test_parses_individual_goe_and_pcs_marks(self) -> None:
        document = pymupdf.open()
        page = document.new_page(width=595, height=842)
        words = [
            (51, 100, "1"),
            (62, 100, "TEST"),
            (267, 100, "USA"),
            (330, 100, "3"),
            (365, 100, "31.50"),
            (410, 100, "20.25"),
            (465, 100, "11.25"),
            (520, 100, "0.00"),
            (166, 120, "Base"),
            (166, 128, "Value"),
            (210, 124, "GOE"),
            (243, 130, "J1"),
            (270, 130, "J2"),
            (297, 130, "J3"),
            (35, 150, "1"),
            (51, 150, "3A"),
            (166, 150, "8.00"),
            (210, 150, "1.00"),
            (247, 150, "2"),
            (274, 150, "1"),
            (301, 150, "0"),
            (45, 180, "Composition"),
            (210, 180, "1.33"),
            (247, 180, "8.00"),
            (274, 180, "8.25"),
            (301, 180, "8.50"),
        ]
        for x, y, text in words:
            page.insert_text((x, y), text)
        content = document.tobytes()
        document.close()

        event = ISUEvent("test", "Test Event", "season2526", "test")
        panel = {
            1: ("Judge One", "ISU"),
            2: ("Judge Two", "ISU"),
            3: ("Judge Three", "ISU"),
        }
        source_url = (
            "https://results.isu.org/results/season2526/test/"
            "FSKMSINGLES-----------QUAL000100--_JudgesDetailsperSkater.pdf"
        )

        rows = _parse_protocol(
            content,
            source_url,
            "sample.pdf",
            "checksum",
            event,
            "men_singles",
            panel,
            {"JUDGE_ONE": {"USA"}, "JUDGE_TWO": {"CAN"}, "JUDGE_THREE": {"JPN"}},
            "https://example.isu.org/officials.pdf",
        )

        self.assertEqual(len(rows), 6)
        self.assertEqual({row["mark_type"] for row in rows}, {"GOE", "PCS"})
        goe_rows = [row for row in rows if row["mark_type"] == "GOE"]
        pcs_rows = [row for row in rows if row["mark_type"] == "PCS"]
        self.assertEqual([row["score"] for row in goe_rows], [2.0, 1.0, 0.0])
        self.assertEqual([row["score"] for row in pcs_rows], [8.0, 8.25, 8.5])
        self.assertEqual(goe_rows[0]["panel_mean"], 1.0)
        self.assertEqual(goe_rows[0]["element_type"], "3A")
        self.assertEqual(goe_rows[0]["base_value"], 8.0)
        self.assertEqual(goe_rows[0]["goe_total"], 1.0)
        self.assertEqual(goe_rows[0]["total_segment_score"], 31.5)
        self.assertEqual(goe_rows[0]["total_element_score"], 20.25)
        self.assertEqual(goe_rows[0]["program_component_score"], 11.25)
        self.assertEqual(goe_rows[0]["total_deductions"], 0.0)
        self.assertEqual(pcs_rows[0]["component"], "Composition")
        self.assertEqual(goe_rows[0]["judge_nationality"], "ISU")
        self.assertEqual(goe_rows[0]["judge_federation"], "USA")
        self.assertEqual(goe_rows[0]["judge_federation_match"], "exact")
        self.assertEqual(
            goe_rows[0]["judge_federation_source_url"],
            "https://example.isu.org/officials.pdf",
        )

    def test_reads_element_values_from_protocol_header_columns(self) -> None:
        for base_column, goe_column in ((158.5, 208.4), (201.3, 233.9)):
            with self.subTest(base_column=base_column):
                document = pymupdf.open()
                page = document.new_page(width=595, height=842)
                for x, y, text in [
                    (base_column, 120, "Base"),
                    (base_column, 128, "Value"),
                    (goe_column, 124, "GOE"),
                    (40.8, 150, "1"),
                    (51.3, 150, "3T+3T"),
                    (base_column + 8, 150, "8.40"),
                    (goe_column + 2, 150, "0.72"),
                ]:
                    page.insert_text((x, y), text)

                words = page.get_text("words")
                columns = _element_column_positions(words)
                line = next(
                    line
                    for line in _lines(words)
                    if any(text == "3T+3T" for _, text in line)
                )
                parsed = _element_row(line, *columns)

                self.assertAlmostEqual(columns[0], base_column, places=4)
                self.assertAlmostEqual(columns[1], goe_column, places=4)
                self.assertEqual(parsed["element_type"], "3T+3T")
                self.assertEqual(parsed["base_value"], 8.4)
                self.assertEqual(parsed["goe_total"], 0.72)
                self.assertEqual(round(parsed["base_value"] + parsed["goe_total"], 2), 9.12)
                document.close()


if __name__ == "__main__":
    unittest.main()
