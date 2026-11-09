# Figure Skating Judging Bias Research

A reproducible research project investigating whether figure-skating scores across men's
singles, women's singles, pair skating, and ice dance vary systematically with entry or
judge nationality, reputation, or other competition context, after accounting for
performance and the official scoring rules.
Anomalies are signals to investigate, not proof of bias or intentional manipulation.

## Project origin

This project grew out of research for a YouTube video about unfairness in figure
skating. It has two connected parts:

- The Jupyter notebook in [`notebooks/bias_analysis.ipynb`](notebooks/bias_analysis.ipynb)
  explores individual GOE and PCS judge marks. It asks whether marks vary with the
  skater's or team's represented country after accounting for competition context,
  whether prior results or technical-call flags relate to scoring, whether judge and
  entry country are associated with mark differences, and which marks stand apart
  from the rest of a panel. These are exploratory questions, not findings that prove
  bias or intent.
- The static [Skate Scores site](docs/) makes the collected protocols easier to
  explore. Visitors can look up skaters and teams, inspect judge marks and official
  totals, filter by competition, and compare performances.

Portraits are added only when a specific image has a verified license that permits
reuse and the required attribution can be shown. Because those licenses and permissions
vary, not every skater can have a portrait; entries without an eligible image use an
initials avatar.

## Status and first milestone

The repeatable collector and exploratory analysis notebook are in place. The first
research milestone is a verifiable proof of concept: collect a limited set of official
protocols, preserve source provenance, parse individual judge scores and technical calls,
then reproduce official totals and rankings before doing any bias analysis. Collected
marks and initial analysis outputs are not yet independently validated research findings.

Start with a small proof of concept using official protocols from the 2022 Winter
Olympics and relevant 2025 and 2026 World Championship or Olympic events across the four
categories: men's singles, women's singles, pair skating, and ice dance. Pair skating and
ice dance are team events, not separate men's and women's competitions. Record any
unavailable or inapplicable event rather than silently substituting another competition.

## Requirements

- Python 3.11 or newer (Python 3.12 is recommended)
- pip

The project is configured for Polars-first data processing, with NumPy, SciPy, and
Statsmodels for analysis. Pandas compatibility, visualizations, notebooks, anomaly
detection, and Bayesian modeling are optional extras.

## Setup

On macOS, install Python 3.12 with Homebrew if you do not already have a compatible
Python installation:

```bash
brew install python@3.12
```

Create and activate the project virtual environment, then install the project and its
development tools:

```bash
$(brew --prefix python@3.12)/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

For an existing Python 3.11+ installation, replace the first command with
`python3 -m venv .venv` after checking `python3 --version`.

Run the tests and linter:

```bash
python -m pytest
python -m ruff check .
```

Install optional tools as needed:

```bash
python -m pip install -e ".[visualization,notebooks]"
# Optional: pandas compatibility, anomaly detection, or Bayesian models
python -m pip install -e ".[compat,anomaly,bayesian]"
```

## Collect official judge scores

Run the collector from the project root with the virtual environment active:

```bash
python -m figure_skating_bias.collectors.isu_results
```

It discovers official per-skater judge-score PDFs from the ISU event indexes for the
European and Four Continents Championships from 2022 through 2026, World Championships
from 2022 and 2024 through 2026, the 2022 and 2026 Winter Olympics, and the supported
ISU Grand Prix events from 2021 through 2025 plus the 2026 Grand Prix de France,
Skate Canada, and Cup of China, and 23 Challenger Series events from 2021
through 2025 with verified per-skater protocols on official ISU or event-results hosts.
External hosts are explicitly allowlisted per event and HTTPS is required. This is not
yet a complete census of senior international events: some Challenger results use
combined PDFs, have inaccessible or unverified indexes, or lack a complete judge panel
for one or more segments. The 2023 World Championship index and the 2021–2023 NHK Trophy
indexes also use legacy combined-PDF formats; the 2021 Grand Prix Final was canceled.
Original protocol PDFs,
event indexes, judge panels, and checksum manifests are cached under `data/raw/`;
normalized individual GOE and PCS judge marks are written to
`data/processed/judge_marks.csv`. Cached sources are reused on later runs; pass
`--refresh` to fetch them again. To use the collector in Python:

```python
from figure_skating_bias.collectors.isu_results import ISUResultsCollector

marks = ISUResultsCollector().collect()
```

Olympic team-event protocols are included as separate `event_type=team_event`
performances and remain distinguishable from the individual Olympic events. They use
the same judge-mark schema; event-specific fields that do not apply are left blank.

Collection requires an internet connection. The collector also downloads the ISU
seasonal officials lists available for 2024/25, 2025/26, and 2026/27 and matches judge names to
their listed member federations. `judge_nationality` preserves the panel label as
published, while `judge_federation` contains the separate-list affiliation. A
federation affiliation is not necessarily citizenship. The verified 2021/22 officials
list URL is not currently configured, and ambiguous or unmatched names are left blank
rather than guessed.

Unresolved affiliations are written to
`data/processed/judge_federation_unmatched.csv`; each event's source manifest records
the list URL and checksum when available. If you have verified the 2021/22 ISU list
URL, pass it when collecting:

```bash
python -m figure_skating_bias.collectors.isu_results \
  --officials-list-url "season2122=<verified-ISU-PDF-URL>"
```

Replace the placeholder with a verified HTTPS PDF URL hosted by an official ISU domain.
In Python, pass the same URL with
`ISUResultsCollector(officials_sources={"season2122": official_pdf_url})`. Validate
parsed marks and affiliations against official sources before treating the CSV as
research-ready.

## Project layout

```text
data/
  raw/          Original protocols and source files (not committed)
  processed/    Normalized, reproducible datasets (not committed)
  external/     Supporting data such as rankings or biographies (not committed)
notebooks/      Exploratory analysis
reports/        Generated research reports and figures
src/figure_skating_bias/
  collectors/   Source retrieval
  parsers/      Protocol parsing
  validation/   Schema, source, and score checks
  analysis/     Nationality, reputation, GOE, PCS, and counterfactual analyses
  models/       Mixed-effects and hierarchical models
  visualization/
  reports/      Report generation
tests/
```

## Free static website

The project includes a static skater and protocol browser in `docs/`. It does not need
a database service or paid hosting. Rebuild the local SQLite database and generate the
JSON files served by GitHub Pages with:

```bash
python -m figure_skating_bias.database
python -m figure_skating_bias.site_export
```

Commit the generated `docs/data/` files and push to the repository. Enable **Settings →
Pages → GitHub Actions** once; `.github/workflows/pages.yml` then publishes the site.
The browser searches skaters/teams, filters competitions, compares two entries, and
aligns matching element types and program components. Entries without a verified
portrait URL use initials avatars.

The ISU collector is intentionally split by responsibility: `isu_results.py` is the
public API and CLI, `isu_results_collector.py` coordinates collection, `isu_sources.py`
handles official downloads and HTML parsing, `isu_officials.py` handles roster
affiliations, `isu_protocol.py` parses judge marks, and `isu_config.py` defines events
and the output schema.

## Data and research safeguards

- Prefer official ISU protocols and retain the original source URL, retrieval date,
  competition identifier, and file checksum for every source document.
- Keep original source files immutable; write parsed and processed data separately.
- Preserve individual judge scores, judge-panel membership, technical calls, deductions,
  represented entry/team nationality, and relevant scoring-rule/season context wherever
  available. Keep pair and ice-dance team members identifiable in separate roster data.
- Validate reconstructed element, segment, total, and ranking results against official
  results before comparing judges or competitions.
- Reproduce the applicable ISU aggregation rules, including treatment of high/low marks,
  before running counterfactuals.
- Distinguish an input error, statistical anomaly, systematic scoring difference,
  potential conflict of interest, and proven intentional manipulation. Do not infer the
  latter from score differences alone.

Raw and generated data directories are ignored by Git by default. Keep source records and
data dictionaries with the project when adding a dataset; do not commit material unless
its terms of use permit redistribution.
