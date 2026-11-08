"""Official ISU source validation, downloading, and HTML parsing."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .isu_config import EVENT_CATEGORIES, RESULTS_HOST

USER_AGENT = "figure-skating-bias-research/0.1 (reproducible academic research)"
ISU_DOCUMENTS_HOST = "isu-d8g8b4b7ece7aphs.a03.azurefd.net"
ISU_HOSTS = {
    RESULTS_HOST,
    "isu.org",
    "www.isu.org",
    "isuresults.com",
    "www.isuresults.com",
    ISU_DOCUMENTS_HOST,
}
PDF_LINK = re.compile(r"_JudgesDetailsperSkater\.pdf$", re.IGNORECASE)
SEGMENT_LINK = re.compile(r"^(SEG\d+)\.htm$", re.IGNORECASE)
JUDGE_ROLE = re.compile(r"Judge\s+No\.?\s*(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class _Link:
    href: str
    text: str


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[_Link] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append(_Link(self._href, " ".join(" ".join(self._text).split())))
            self._href = None
            self._text = []


class _TableRowParser(HTMLParser):
    """Read table rows while retaining nested country-table text in its parent cell."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row_stack: list[list[str]] = []
        self._cell_stack: list[tuple[list[str], list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._row_stack.append([])
        elif tag in {"td", "th"}:
            if self._row_stack:
                self._cell_stack.append((self._row_stack[-1], []))

    def handle_data(self, data: str) -> None:
        for _, cell in self._cell_stack:
            cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._cell_stack:
            row, cell = self._cell_stack.pop()
            row.append(" ".join(" ".join(cell).split()))
        elif tag == "tr" and self._row_stack:
            row = self._row_stack.pop()
            if row:
                self.rows.append(row)


def _validate_official_url(url: str, trusted_hosts: tuple[str, ...] = ()) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ISU_HOSTS | set(trusted_hosts):
        raise ValueError(
            "Only HTTPS URLs hosted at an official ISU host or a configured "
            f"event-results host are accepted: {url}"
        )


def _download(
    url: str,
    path: Path,
    refresh: bool,
    delay_seconds: float,
    trusted_hosts: tuple[str, ...] = (),
) -> bytes:
    _validate_official_url(url, trusted_hosts)
    if path.is_file() and not refresh:
        return path.read_bytes()

    if delay_seconds > 0:
        time.sleep(delay_seconds)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=60) as response:
            _validate_official_url(response.geturl(), trusted_hosts)
            content = response.read()
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Could not download official ISU source {url}: {exc}") from exc

    if not content:
        raise ValueError(f"Official ISU source is empty: {url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _event_category(filename: str) -> str | None:
    if filename.startswith("FSKXTEAM"):
        discipline = re.search(r"(?:QUAL|FNL-)\d{4}(MN|LD|PR|DC)--", filename)
        if discipline is None:
            raise ValueError(f"Unsupported team-event protocol discipline: {filename}")
        return {
            "MN": "men_singles",
            "LD": "women_singles",
            "PR": "pair_skating",
            "DC": "ice_dance",
        }[discipline.group(1)]
    for prefix, category in EVENT_CATEGORIES.items():
        if filename.startswith(prefix):
            return category
    raise ValueError(f"Unsupported ISU protocol type in filename: {filename}")


def _segment(filename: str, event_category: str) -> str:
    if "QUAL" in filename:
        return "rhythm_dance" if event_category == "ice_dance" else "short_program"
    if "FNL" in filename:
        return "free_dance" if event_category == "ice_dance" else "free_skating"
    raise ValueError(f"Could not identify program segment in official PDF name: {filename}")


def _official_sources(index_url: str, html: str) -> list[tuple[str, str, str]]:
    parser = _AnchorParser()
    parser.feed(html)
    sources: list[tuple[str, str, str]] = []
    for index, link in enumerate(parser.links):
        if not PDF_LINK.search(link.href):
            continue
        category = _event_category(Path(link.href).name)
        if category is None:
            continue
        previous_segment = next(
            (
                SEGMENT_LINK.fullmatch(Path(candidate.href).name)
                for candidate in reversed(parser.links[:index])
                if SEGMENT_LINK.fullmatch(Path(candidate.href).name)
            ),
            None,
        )
        if previous_segment is None:
            raise ValueError(f"Could not associate protocol PDF with segment page: {link.href}")
        segment_code = previous_segment.group(1).upper()
        pdf_url = urljoin(index_url, link.href)
        panel_url = urljoin(index_url, f"{segment_code}OF.htm")
        sources.append((pdf_url, panel_url, category))
    if not sources:
        raise ValueError(f"No per-skater judge-score PDFs found on official index: {index_url}")
    return sources


def _judge_panel(html: str, source_url: str) -> dict[int, tuple[str, str]]:
    parser = _TableRowParser()
    parser.feed(html)
    panel: dict[int, tuple[str, str]] = {}
    for cells in parser.rows:
        if len(cells) < 3:
            continue
        match = JUDGE_ROLE.fullmatch(cells[0].strip())
        if match is None:
            continue
        number = int(match.group(1))
        name, nationality = cells[1].strip(), cells[2].strip().upper()
        if not name or not nationality:
            raise ValueError(f"Incomplete official judge panel row in {source_url}: {cells}")
        panel[number] = (name, nationality)
    if not panel:
        raise ValueError(f"No judge panel found on official ISU page: {source_url}")
    return panel
