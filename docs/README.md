# Skate Scores

Skate Scores grew out of research for a YouTube video investigating unfairness in
figure skating. The companion [`bias_analysis.ipynb`](../notebooks/bias_analysis.ipynb)
explores whether individual judge GOE and PCS marks vary with represented country,
competition context, prior results, technical-call flags, or judge-entry country. It
also looks for marks that depart from the rest of a panel. This exploratory analysis
does not establish that bias or intentional manipulation exists.

This GitHub Pages site is the interactive companion: browse official protocols,
inspect judge marks and totals, filter competitions, and compare skaters or teams.
Portraits appear only when their reuse license and attribution requirements permit
publication, so some entries use initials instead of an image.
When comparing two entries, the competition selector and results are limited to
competitions and performances shared by both.

This is a static website. It runs in a visitor's browser and reads generated JSON
files from `docs/data/`; it does not use a server, API key, or hosted database.

## Copyright and reuse

Original project materials owned by Nadin Katrin Apel are all rights reserved;
see the project [copyright notice](../LICENSE) and the website's
[copyright and reuse page](./license.html). Third-party materials, including
official skating data and photographs, may have separate rights and licenses.

## Program calculator

The program calculator compares two hypothetical segment scores using the singles
and pairs scale in ISU Communication 2786 (updated June 2, 2026). Select an
element by its ISU code and a GOE grade; its base and GOE values come directly
from the published table. Clean jump combinations and sequences can be entered
as codes joined with `+` (e.g. `3Lz+3T` or `3F+Eu+3S`); GOE is based on the
most difficult jump. For combinations, technical calls, quintuple jumps, bonuses
and repeated-jump reductions are not supported. The estimate appears once an
element is selected, with a default GOE of zero. PCS is excluded until all three
already-averaged marks and the applicable factor are entered. The calculator
rounds each factored component separately and adds it to the technical score.
It subtracts the number of falls multiplied by the per-fall deduction (default
1 point). This fixed-rate estimate does not apply other deductions or escalating
fall penalties automatically.

This is a planning estimate, not an official scoring system: users must apply the
relevant season's technical calls, program requirements, bonuses, deductions,
and component factors themselves. Bonus and repeated-jump reductions are not
calculated. A single selected GOE is not a panel's trimmed average. Check the
linked ISU rules. Calculator inputs are not saved after leaving the page.

## Build or refresh the site data

From the project root, with the project virtual environment active:

```bash
python -m figure_skating_bias.database
python -m figure_skating_bias.site_export
```

The export writes a small searchable entry index and one protocol JSON file per
skater/team under `docs/data/`. Commit the updated `docs/` folder to publish the
latest dataset.

To collect current official sources first, run:

```bash
python -m figure_skating_bias.collectors.isu_results
python -m figure_skating_bias.database
python -m figure_skating_bias.site_export
```

## Publish on GitHub Pages

Push the project to a GitHub repository, then open **Settings → Pages** and choose
**GitHub Actions** as the build and deployment source. The workflow at
`.github/workflows/pages.yml` publishes the `docs/` folder. GitHub Pages hosting is
free for public repositories; this project does not require separate database hosting.

The site includes official protocol links and judge-by-judge scores. Entries without
a verified, reusable portrait image display an initials avatar instead. Portraits
from Wikimedia Commons are used only when their file pages identify a reuse license;
the site displays the photographer and license links beside each portrait.
For each segment, the score tables include the protocol's official Total Element
Score, factored Program Component Score, and Total Points (the official total
segment score). Total Points appears once, below the factored component score.
The component subtotal is read from the PDF rather than inferred from un-factored
judge marks.

The athlete directory is grouped into Women Single Skating, Men Single Skating, Ice
Dance, and Pair Skating. A portrait mapping in `data/portraits.json` records each
image URL together with its source page, creator, and license. The exporter uses this
file by default. Only add an image after checking that the individual file's license
permits reuse and recording all required attribution details:

```bash
python -m figure_skating_bias.site_export --portraits data/portraits.json
```

The welcome dialog uses Nadin's profile photo and links to her Buy Me a Coffee,
LinkedIn, and YouTube pages. It appears on the first visit and can be reopened from
the footer on either page. The navigation highlights the current page or section;
on the scores page it also includes the project credit and a YouTube link.

For example:

```json
{
  "USA:ILIA_MALININ": {
    "url": "https://example.org/licensed/ilia-malinin.jpg",
    "source_url": "https://example.org/photo-page",
    "title": "Photo title",
    "creator": "Photographer name",
    "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/"
  }
}
```
