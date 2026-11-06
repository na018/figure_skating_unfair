# Figure Skating Judging Bias Research

A reproducible research project investigating whether women's singles figure-skating
scores vary systematically with skater or judge nationality, reputation, or other
competition context, after accounting for performance and the official scoring rules.
Anomalies are signals to investigate, not proof of bias or intentional manipulation.

## Status and first milestone

This repository is the project scaffold. It does not yet contain collected protocols,
parsed scores, results, or findings. The first milestone is a small, verifiable proof of
concept: collect a limited set of official protocols, preserve source provenance, parse
individual judge scores and technical calls, then reproduce official totals and rankings
before doing any bias analysis.

Start with the 2022 Winter Olympics and relevant 2025 and 2026 World Championship or
Olympic women's singles protocols. Record any unavailable or inapplicable event rather
than silently substituting another competition.

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

## Data and research safeguards

- Prefer official ISU protocols and retain the original source URL, retrieval date,
  competition identifier, and file checksum for every source document.
- Keep original source files immutable; write parsed and processed data separately.
- Preserve individual judge scores, judge-panel membership, technical calls, deductions,
  and relevant scoring-rule/season context wherever available.
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
