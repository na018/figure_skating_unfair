# Data directory

The data supports an exploratory project that began with research for a YouTube video
about potential unfairness in figure skating. The companion
[`bias_analysis.ipynb`](../notebooks/bias_analysis.ipynb) examines individual judge
marks and possible relationships with represented country, competition context,
reputation, technical calls, and judge-entry country. These analyses are exploratory:
score patterns alone do not prove bias or intent. A separate static website in
[`docs/`](../docs/) lets visitors explore protocols, judge marks, and official totals.

Store immutable source protocols in `raw/`, normalized datasets in `processed/`, and
supporting reference data in `external/`. These directories are ignored by Git so that
large or externally sourced files are not committed accidentally.

For each source document, record at least its competition ID, source URL, retrieval date,
original filename, and a SHA-256 checksum in a source manifest. Never overwrite the
original protocol with parsed or corrected data. Document corrections and retain the
original value alongside any corrected value.

The analysis dataset should identify the event category (`men_singles`, `women_singles`,
`pair_skating`, or `ice_dance`) and use a stable entry ID. For singles, an entry is one
skater; for pair skating and ice dance, an entry is a team with its represented country.
Keep team-member identities and nationalities in separate roster data when needed.
Collector-generated entry IDs normalize name order, punctuation, and diacritics and include
the represented country. They are useful for repeat appearances with consistent official
names, but are not an authoritative athlete registry; validate aliases, team changes, and
country changes before calculating athlete-level reputation measures.

The repeatable ISU collector is available as
`python -m figure_skating_bias.collectors.isu_results`. It collects European and Four
Continents Championships from 2022 through 2026, World Championships from 2022 and 2024
through 2026, the 2022 and 2026 Winter Olympics, and the supported ISU Grand Prix events
from 2021 through 2025 plus the 2026 Grand Prix de France, Skate Canada, and Cup of
China, and 23 Challenger Series events from 2021 through 2025 whose
official result pages provide compatible per-skater protocols. Non-ISU event-results
hosts are explicitly allowlisted per event and HTTPS is required. This is not a complete
census of senior international competitions: some Challenger results use combined PDFs,
have inaccessible or unverified indexes, lack a complete judge panel for a segment, or
need a different parser. The 2023 World Championship index and the 2021–2023 NHK Trophy
indexes also use legacy combined-PDF formats; the 2021 Grand Prix Final was canceled.
The collector caches official event
indexes, judge-panel pages, per-skater score PDFs, and available seasonal officials lists
in `raw/`, including SHA-256 checksums in event-level manifests, and writes parsed marks
to `processed/judge_marks.csv`.

## What is and is not included

The current dataset contains 73 configured competition IDs and 659 per-skater judge-score
PDFs (331 short/rhythm-segment PDFs and 328 free-segment PDFs). The protocol set includes
557 individual senior, 74 junior, and 12 advanced-novice PDFs, plus eight team-event
protocols from each of the 2022 and 2026 Olympics. It includes individual judge marks
only when an event index links to a per-skater protocol PDF the parser can read and an
official segment panel page identifies the judges in its J-number columns.
The parser checks that marks map to the panel and that each scored item has one mark
from each listed judge; it raises an error rather than guessing at missing identities
or silently accepting a mismatched panel. Combined/legacy PDFs and unsupported or
unavailable result pages are not represented in the current dataset.

An unknown or unmatched **judge federation** does not exclude marks. The marks remain
in the dataset, with the affiliation unavailable or unmatched, because federation
matching is separate from identifying the judge on the event panel. Judge nationality
is the panel label; judge federation is the affiliation listed in the officials data.

Segment coverage is not identical for every event and discipline. Among senior protocols,
short and free segments are present for 71 competitions each in men’s singles and
women’s singles, for 68 and 67 competitions respectively in pairs, and for 69
competitions each in ice dance. Junior and advanced-novice events are also present and
are kept separate from senior segments in the database. A missing discipline/segment
means no parsed marks are available for that combination; it does not mean the segment
had zero scores. Olympic 2022 and 2026 team-event protocols are included separately as
`event_type=team_event`, across the four disciplines and their short/free segments; the
individual protocols use `event_type=individual_event`.

## Building the database

Build a normalized SQLite database from the existing processed CSV and event manifests:

```bash
python -m figure_skating_bias.database
```

By default this writes `data/processed/figure_skating.sqlite3`. The database and source
data remain in Git-ignored `data/` directories. To use different paths:

```bash
python -m figure_skating_bias.database \
  --csv data/processed/judge_marks.csv \
  --raw-dir data/raw \
  --output data/processed/figure_skating.sqlite3
```

The schema separates competitions, event segments (including senior, junior, and
advanced-novice divisions), entries, performances, judges, judge assignments,
individual marks, and source documents. Division is read from the official protocol
filename. `performances.entry_name` and `entry_nationality` preserve the official label
for that appearance. An `entry_id`
is a useful search key, not an authoritative lifelong athlete identity—particularly
for teams, name aliases, and country changes. Each mark links to its judge assignment
and source protocol, and `source_documents` retains manifest URLs, filenames, hashes,
and availability status.

SQLite is the local/build-time source of truth. A GitHub Pages site is static and cannot
run server-side SQLite queries, so a future site should publish generated JSON search
indexes and per-skater result files from this database rather than ask browsers to
download the entire database. The static site in `docs/` includes a searchable index of
1,125 skater/team entries and their per-entry protocols; generate or refresh the JSON
files with `python -m figure_skating_bias.site_export`. The database is only used
locally to prepare the static files; no database hosting is needed.

`judge_nationality` is the label shown in the event panel, which may be `ISU` rather than
a country. `judge_federation` is matched from the seasonal officials list and records
the listed member federation, not necessarily citizenship. The collector does not guess
when names are ambiguous or unmatched; those cases, including seasons without a
configured list, are recorded in `processed/judge_federation_unmatched.csv`. The
verified 2021/22 officials-list URL is not currently configured. A verified official
PDF URL can be supplied with `--officials-list-url SEASON=URL` or via the
`officials_sources` argument to `ISUResultsCollector`.
