"""Parse individual GOE and PCS judge marks from official ISU PDFs."""

from __future__ import annotations

import re
import statistics
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import pymupdf

from .isu_config import ISUEvent
from .isu_officials import _judge_federation, _judge_identity
from .isu_sources import _segment

NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")


def _numeric(value: str) -> float | None:
    value = value.strip().replace(",", ".")
    if not NUMBER.fullmatch(value):
        return None
    return float(value)


def _entry_identity(name: str, nationality: str) -> str:
    normalized_name = unicodedata.normalize("NFKD", name)
    name_tokens = re.findall(
        r"[A-Z0-9]+",
        "".join(char for char in normalized_name if not unicodedata.combining(char)).upper(),
    )
    if not name_tokens:
        raise ValueError(f"Could not create a stable ID from entry name: {name}")
    return f"{nationality}:{'_'.join(sorted(name_tokens))}"


def _lines(words: list[tuple]) -> list[list[tuple[float, str]]]:
    rows: list[list[tuple[float, float, str]]] = []
    for word in sorted(words, key=lambda item: (item[1], item[0])):
        x0, y0, _, _, text = word[:5]
        if rows and abs(rows[-1][0][0] - y0) <= 1.8:
            rows[-1].append((float(y0), float(x0), str(text)))
        else:
            rows.append([(float(y0), float(x0), str(text))])
    return [sorted([(x, text) for _, x, text in row], key=lambda item: item[0]) for row in rows]


def _entry_header(line: list[tuple[float, str]]) -> tuple[int, str, str] | None:
    rank = next(
        (int(text) for x, text in line if x < 60 and text.isdigit() and 0 < int(text) < 1000),
        None,
    )
    name_parts = [text for x, text in line if 55 <= x < 230]
    noc = next(
        (text for x, text in line if 230 <= x < 320 and re.fullmatch(r"[A-Z]{3}", text)),
        None,
    )
    if rank is None or not name_parts or noc is None:
        return None
    return rank, " ".join(name_parts), noc


def _segment_scores(line: list[tuple[float, str]]) -> dict[str, float | None]:
    noc_x = next(
        (
            x for x, text in line
            if 230 <= x < 320 and re.fullmatch(r"[A-Z]{3}", text)
        ),
        None,
    )
    if noc_x is None:
        return {
            "total_segment_score": None,
            "total_element_score": None,
            "program_component_score": None,
            "total_deductions": None,
        }
    values = [
        value for x, text in line
        if x > noc_x and (value := _numeric(text)) is not None
    ]
    if len(values) < 5:
        return {
            "total_segment_score": None,
            "total_element_score": None,
            "program_component_score": None,
            "total_deductions": None,
        }
    segment_score, element_score, component_score, deductions = values[-4:]
    return {
        "total_segment_score": segment_score,
        "total_element_score": element_score,
        "program_component_score": component_score,
        "total_deductions": deductions,
    }


def _judge_columns(lines: list[list[tuple[float, str]]]) -> dict[int, float]:
    columns: dict[int, float] = {}
    for line in lines:
        for x, text in line:
            match = re.fullmatch(r"J([1-9])", text)
            if match:
                columns[int(match.group(1))] = x
    return columns


def _scores_for_judges(
    line: list[tuple[float, str]], columns: dict[int, float]
) -> dict[int, float]:
    values: dict[int, float] = {}
    for number, column_x in columns.items():
        candidates = [
            (abs(x - column_x), value) for x, text in line if (value := _numeric(text)) is not None
        ]
        if candidates:
            distance, value = min(candidates, key=lambda item: item[0])
            if distance <= 13:
                values[number] = value
    return values


def _element_column_positions(words: list[tuple]) -> tuple[float, float] | None:
    header_words = [
        word for word in words
        if word[1] < 250 and str(word[4]).casefold() in {"base", "goe"}
    ]
    base_headers = [word for word in header_words if str(word[4]).casefold() == "base"]
    goe_headers = [word for word in header_words if str(word[4]).casefold() == "goe"]
    if not base_headers or not goe_headers:
        return None
    base_header = min(base_headers, key=lambda word: word[1])
    goe_header = min(goe_headers, key=lambda word: word[1])
    return float(base_header[0]), float(goe_header[0])


def _element_row(
    line: list[tuple[float, str]], base_column: float, goe_column: float
) -> dict[str, object] | None:
    number = next(
        (int(text) for x, text in line if x < 45 and text.isdigit() and 0 < int(text) < 100),
        None,
    )
    description = [
        text for x, text in line
        if 45 <= x < base_column - 15 and _numeric(text) is None
    ]

    def value_at_column(column: float) -> float | None:
        candidates = [
            (abs(x - column), value)
            for x, text in line
            if (value := _numeric(text)) is not None
        ]
        if not candidates:
            return None
        distance, value = min(candidates, key=lambda item: item[0])
        return value if distance <= 15 else None

    base_value = value_at_column(base_column)
    goe_total = value_at_column(goe_column)
    if number is None or not description or base_value is None:
        return None
    flags = [
        text for x, text in line
        if base_column - 15 <= x < goe_column - 10 and _numeric(text) is None
    ]
    return {
        "element_number": number,
        "element_type": " ".join(description),
        "base_value": base_value,
        "technical_call": " ".join(flags) or None,
        "goe_total": goe_total,
    }


def _component_row(line: list[tuple[float, str]]) -> tuple[str, float] | None:
    label_parts = [text for x, text in line if 45 <= x < 180]
    factor = next(
        (value for x, text in line if 225 <= x < 260 and (value := _numeric(text)) is not None),
        None,
    )
    joined = " ".join(label_parts).strip()
    known_components = {
        "composition",
        "presentation",
        "skating skills",
        "transitions",
        "performance",
        "interpretation",
        "choreography",
    }
    if factor is None or joined.casefold() not in known_components:
        return None
    return joined, factor


def _parse_protocol(
    content: bytes,
    pdf_url: str,
    source_file: str,
    source_sha256: str,
    event: ISUEvent,
    event_category: str,
    panel: dict[int, tuple[str, str]],
    officials_roster: dict[str, set[str]] | None = None,
    officials_list_url: str | None = None,
) -> list[dict[str, object]]:
    document = pymupdf.open(stream=content, filetype="pdf")
    parsed: list[dict[str, object]] = []
    pdf_name = Path(urlparse(pdf_url).path).name
    segment = _segment(pdf_name, event_category)
    event_type = "team_event" if pdf_name.startswith("FSKXTEAM") else "individual_event"
    columns: dict[int, float] = {}
    element_columns: tuple[float, float] | None = None

    for page in document:
        words = page.get_text("words")
        lines = _lines(words)
        page_element_columns = _element_column_positions(words)
        if page_element_columns is not None:
            element_columns = page_element_columns
        page_columns = _judge_columns(lines)
        if page_columns:
            columns = page_columns
        if not columns:
            continue
        active_entry: tuple[int, str, str] | None = None
        active_scores: dict[str, float | None] = {}
        for line in lines:
            header = _entry_header(line)
            if header is not None:
                active_entry = header
                active_scores = _segment_scores(line)
                continue
            if active_entry is None:
                continue
            judge_scores = _scores_for_judges(line, columns)
            if not judge_scores:
                continue

            element = (
                _element_row(line, *element_columns)
                if element_columns is not None
                else None
            )
            component = _component_row(line)
            if element is None and component is None:
                continue

            mark_type = "GOE" if element is not None else "PCS"
            for judge_number, score in judge_scores.items():
                if judge_number not in panel:
                    raise ValueError(
                        f"Protocol has J{judge_number}, but panel page has no matching "
                        f"judge: {pdf_url}"
                    )
                judge_name, judge_nationality = panel[judge_number]
                judge_federation, federation_match = _judge_federation(judge_name, officials_roster)
                rank, entry_name, entry_nationality = active_entry
                parsed.append(
                    {
                        "competition_id": event.competition_id,
                        "competition_name": event.competition_name,
                        "season": event.season,
                        "scoring_rule_version": event.season,
                        "event_category": event_category,
                        "event_type": event_type,
                        "segment": segment,
                        "entry_id": _entry_identity(entry_name, entry_nationality),
                        "entry_name": entry_name,
                        "entry_nationality": entry_nationality,
                        "rank": rank,
                        **active_scores,
                        "judge_id": _judge_identity(judge_name),
                        "judge_panel_assignment": (
                            f"{event.competition_id}:{event_type}:{segment}:J{judge_number}"
                        ),
                        "judge_name": judge_name,
                        "judge_nationality": judge_nationality,
                        "judge_federation": judge_federation,
                        "judge_federation_match": federation_match,
                        "judge_federation_source_url": officials_list_url,
                        "mark_type": mark_type,
                        "element_number": element["element_number"] if element else None,
                        "element_type": element["element_type"] if element else None,
                        "base_value": element["base_value"] if element else None,
                        "technical_call": element["technical_call"] if element else None,
                        "goe_total": element["goe_total"] if element else None,
                        "component": component[0] if component else None,
                        "component_factor": component[1] if component else None,
                        "score": score,
                        "source_url": pdf_url,
                        "source_file": source_file,
                        "source_sha256": source_sha256,
                    }
                )

    document.close()
    if not parsed:
        raise ValueError(f"No individual judge marks could be parsed from {pdf_url}")

    score_groups: dict[tuple, list[float]] = {}
    assignment_groups: dict[tuple, set[str]] = {}
    for row in parsed:
        key = (
            row["competition_id"],
            row["event_category"],
            row["segment"],
            row["entry_id"],
            row["mark_type"],
            row["element_number"],
            row["component"],
        )
        score_groups.setdefault(key, []).append(float(row["score"]))
        assignment_key = (*key, row["judge_panel_assignment"])
        if assignment_key in assignment_groups:
            raise ValueError(f"Duplicate judge mark in {pdf_url}: {assignment_key}")
        assignment_groups[assignment_key] = {str(row["judge_id"])}
    for row in parsed:
        key = (
            row["competition_id"],
            row["event_category"],
            row["segment"],
            row["entry_id"],
            row["mark_type"],
            row["element_number"],
            row["component"],
        )
        scores = score_groups[key]
        if len(scores) != len(panel):
            raise ValueError(
                f"Expected {len(panel)} judge marks for {key} in {pdf_url}, found {len(scores)}."
            )
        row["panel_mean"] = statistics.mean(scores)
        row["panel_median"] = statistics.median(scores)
    return parsed
