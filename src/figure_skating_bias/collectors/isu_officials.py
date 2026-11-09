"""Seasonal ISU officials-list parsing and judge federation matching."""

from __future__ import annotations

import re
import unicodedata

import pymupdf

OFFICIALS_LIST_URLS = {
    "season2122": None,
    "season2425": (
        "https://isu-d8g8b4b7ece7aphs.a03.azurefd.net/isudamcontainer/CMS/"
        "isucommunications/pdf/"
        "2663ListOfficialsFSIDSYS202425updatedOct3rd056185800_17328046745865.pdf"
    ),
    "season2526": (
        "https://isu-d8g8b4b7ece7aphs.a03.azurefd.net/isudamcontainer/CMS/"
        "Corporate-Site/Governance/Transparency/ISU-Communications/"
        "2735-List-Officials-FS-ID-SYS-2025-26-1754294295-5479.pdf"
    ),
    "season2627": (
        "https://isu-d8g8b4b7ece7aphs.a03.azurefd.net/isudamcontainer/CMS/"
        "Corporate-Site/Governance/Transparency/ISU-Communications/"
        "2816-List-Officials-FS-ID-SYS-2026-27-1787574191-9463.pdf"
    ),
}


def _judge_identity(name: str) -> str:
    tokens = [
        token
        for token in re.findall(r"[A-Z]+", name.upper())
        if token not in {"MR", "MRS", "MS", "MISS", "DR"}
    ]
    if not tokens:
        raise ValueError(f"Could not create a stable ID from judge name: {name}")
    return "_".join(sorted(tokens))


def _officials_identity(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return _judge_identity(ascii_name)


def _officials_roster(content: bytes, source_url: str) -> dict[str, set[str]]:
    document = pymupdf.open(stream=content, filetype="pdf")
    roster: dict[str, set[str]] = {}
    country_heading = re.compile(r"^([A-Z]{3})\s*-\s*.+$")
    name_line = re.compile(
        r"^(.+),\s*(?:Mr|Mrs|Ms|Miss)\.?\s*$",
        re.IGNORECASE,
    )
    official_role = re.compile(r"^(?:ISU|International)\s+(.+)$", re.IGNORECASE)

    for page in document:
        country: str | None = None
        collecting_officials = False
        for raw_line in page.get_text().splitlines():
            line = " ".join(raw_line.split())
            country_match = country_heading.fullmatch(line)
            if country_match is not None:
                country = country_match.group(1)
                collecting_officials = False
                continue

            role_match = official_role.fullmatch(line)
            if role_match is not None:
                role = role_match.group(1).casefold()
                collecting_officials = role in {"judge", "referee"}
                continue

            if not country or not collecting_officials:
                continue
            name_match = name_line.fullmatch(line)
            if name_match is not None:
                identity = _officials_identity(name_match.group(1))
                roster.setdefault(identity, set()).add(country)

    document.close()
    if not roster:
        raise ValueError(f"No judge or referee affiliations found in official list: {source_url}")
    return roster


def _judge_federation(
    name: str,
    roster: dict[str, set[str]] | None,
) -> tuple[str | None, str]:
    if roster is None:
        return None, "source_unavailable"

    federations = roster.get(_officials_identity(name), set())
    if len(federations) == 1:
        return next(iter(federations)), "exact"
    if len(federations) > 1:
        return None, "ambiguous"
    return None, "unmatched"
