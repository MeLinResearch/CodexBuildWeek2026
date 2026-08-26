# LinForensics report assets

Generated, brand-matched HTML for liforensics.com. Everything here is built from
machine-readable output of the analysis engine in
[`MeLinResearch/Updgrade`](https://github.com/MeLinResearch/Updgrade) — no figure
and no excerpt on any page is typed in by hand.

## What's in here

| File | What it is |
|---|---|
| `sample-report-annotated.html` | **The website asset.** A complete sample customer report with numbered callouts and drawn arrows explaining each part in plain language. |
| `sample-report.html` | The same report on its own, no annotations — for a "sample deliverable" download or print. |
| `lin-test-report.html` | Internal test & coverage evidence for the engine. |
| `lf_theme.py` | Single source of truth for the LinForensics palette and type stacks. |
| `build_sample_case.py` | Runs a synthetic case through the real engine and saves the result. |
| `generate_sample_report.py` | Renders the customer report, plain or annotated. |
| `generate_test_report.py` | Renders the test & coverage report. |
| `data/` | Raw inputs: engine output, pytest JSON, coverage JSON, JUnit XML. |

## Colour scheme

Every colour resolves through the tokens in `lf_theme.py`, sampled from
liforensics.com — indigo `#4F46E5` on near-black `#0B1220` over white and
`#F8FAFC`, with `#EEF2FF` for soft brand fills. Change a value there and all
three pages follow on the next build.

Headings use Plus Jakarta Sans from Google Fonts with a system-sans fallback. If
the live site uses a different face, change `FONT_STACK` in `lf_theme.py`.

## Regenerating

The engine lives in a separate repository, so point the build at a checkout of it:

```bash
git clone https://github.com/MeLinResearch/Updgrade /path/to/updgrade
cd /path/to/updgrade
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest pytest-cov pytest-json-report
```

### Customer-facing sample

```bash
python reports/build_sample_case.py --engine-root /path/to/updgrade
python reports/generate_sample_report.py --mode annotated
python reports/generate_sample_report.py --mode plain
```

### Test & coverage report

The suite runs with no credentials and no network. Eight route tests reach the
extractor, which the engine resolves through `RUNNER_IMPORT_PATH`; point that at
`data/offline_runner.py` so they run deterministically:

```bash
cd /path/to/updgrade
PYTHONPATH=/path/to/reports/data RUNNER_IMPORT_PATH="offline_runner:extract_instances_runner" \
  .venv/bin/python -m pytest tests -q \
    --json-report --json-report-file=/path/to/reports/data/report.json \
    --cov=engine --cov=api --cov=api_v1 \
    --cov-report=json:/path/to/reports/data/coverage.json

python reports/generate_test_report.py --commit "$(git rev-parse --short HEAD)"
```

## Embedding in the site

Each generator takes `--fragment` to emit body markup only, without the
`<!doctype>` / `<head>` shell, for dropping into an existing page or CMS block:

```bash
python reports/generate_sample_report.py --mode annotated --fragment --out annotated.part.html
```

The annotated page needs its inline `<script>` to draw the arrows. Below 1080px
the arrows are hidden and the callouts stack under the report automatically, so
the numbered pins still tie each note to its section on mobile.
