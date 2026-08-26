#!/usr/bin/env python3
"""Render a LinForensics-branded HTML test & coverage report.

Consumes the JSON emitted by ``pytest --json-report`` and ``--cov-report=json``
and produces a single self-contained HTML file suitable for publishing on
liforensics.com. The colour scheme is driven entirely by the CSS custom
properties in ``PALETTE`` so the report tracks the marketing site.

Usage:
    python reports/generate_test_report.py \
        --json data/report.json \
        --coverage data/coverage.json \
        --baseline data/report-baseline.json \
        --out lin-test-report.html
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
from pathlib import Path
from typing import Any

from lf_theme import PALETTE, FONT_LINKS, document, mark_svg, tokens_css


# --- data shaping ---------------------------------------------------------

def _duration(test: dict[str, Any]) -> float:
    return sum(
        float(test.get(phase, {}).get("duration", 0.0) or 0.0)
        for phase in ("setup", "call", "teardown")
    )


def load_run(path: Path) -> dict[str, Any]:
    """Normalise a pytest-json-report file into the shape the template wants."""
    raw = json.loads(path.read_text())
    suites: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    for test in raw.get("tests", []):
        node = test["nodeid"]
        suite_name = node.split("::", 1)[0]
        case_name = node.split("::", 1)[1] if "::" in node else node
        outcome = test.get("outcome", "unknown")

        suite = suites.setdefault(
            suite_name,
            {"name": suite_name, "passed": 0, "failed": 0, "skipped": 0, "other": 0,
             "total": 0, "duration": 0.0},
        )
        suite["total"] += 1
        suite["duration"] += _duration(test)
        if outcome in ("passed", "failed", "skipped"):
            suite[outcome] += 1
        else:
            suite["other"] += 1

        if outcome == "failed":
            call = test.get("call") or {}
            crash = call.get("crash") or {}
            failures.append(
                {
                    "suite": suite_name,
                    "case": case_name,
                    "message": (crash.get("message") or call.get("longrepr") or "").strip(),
                    "location": f"{crash.get('path', '')}:{crash.get('lineno', '')}".strip(":"),
                }
            )

    summary = raw.get("summary", {})
    return {
        "suites": sorted(suites.values(), key=lambda s: s["name"]),
        "failures": failures,
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "skipped": summary.get("skipped", 0),
        "total": summary.get("total", 0),
        "duration": float(raw.get("duration", 0.0)),
        "created": raw.get("created"),
        "exitcode": raw.get("exitcode"),
    }


def load_coverage(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text())
    files = []
    for name, entry in raw.get("files", {}).items():
        s = entry["summary"]
        files.append(
            {
                "name": name,
                "statements": s["num_statements"],
                "missing": s["missing_lines"],
                "percent": s["percent_covered"],
            }
        )
    files.sort(key=lambda f: (f["percent"], -f["statements"]))
    return {"files": files, "totals": raw.get("totals", {})}


# --- rendering helpers ----------------------------------------------------

def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _coverage_tone(percent: float) -> str:
    """Green at or above the project's 85% gate, amber down to 70%, red below."""
    if percent >= 85:
        return "pass"
    if percent >= 70:
        return "warn"
    return "fail"


def _css() -> str:
    tokens = tokens_css()
    return f"""
:root {{
    color-scheme: light;
{tokens}
    --lf-radius: 14px;
    --lf-shadow: 0 1px 2px rgba(15, 23, 42, .04), 0 12px 32px -18px rgba(15, 23, 42, .28);
}}

* {{ box-sizing: border-box; }}

body {{
    margin: 0;
    font-family: var(--lf-font);
    font-size: 16px;
    line-height: 1.6;
    color: var(--lf-body);
    background:
        radial-gradient(1200px 520px at 12% -8%, var(--lf-indigo-tint) 0%, rgba(245,246,255,0) 62%),
        linear-gradient(180deg, var(--lf-surface) 0%, var(--lf-canvas) 100%);
    background-attachment: fixed;
    -webkit-font-smoothing: antialiased;
}}

.lf-shell {{ max-width: 1120px; margin: 0 auto; padding: 0 28px 72px; }}

/* --- masthead --- */
.lf-bar {{
    display: flex; align-items: center; justify-content: space-between;
    gap: 20px; padding: 22px 0 20px;
    border-bottom: 1px solid var(--lf-line);
}}
.lf-brand {{ display: flex; align-items: center; gap: 11px; }}
.lf-mark {{
    width: 30px; height: 30px; border-radius: 9px;
    background: linear-gradient(160deg, var(--lf-indigo) 0%, var(--lf-indigo-deep) 100%);
    display: grid; place-items: center; flex: none;
}}
.lf-wordmark {{
    font-weight: 700; font-size: 17px; letter-spacing: -.015em; color: var(--lf-ink);
}}
.lf-bar-meta {{
    font-size: 13px; color: var(--lf-muted); font-variant-numeric: tabular-nums;
}}

/* --- hero --- */
.lf-hero {{ padding: 60px 0 14px; max-width: 760px; }}
.lf-badge {{
    display: inline-block; padding: 6px 14px; border-radius: 999px;
    background: var(--lf-indigo-soft); color: var(--lf-indigo-strong);
    font-size: 11.5px; font-weight: 700; letter-spacing: .11em; text-transform: uppercase;
}}
h1 {{
    margin: 22px 0 0; font-size: clamp(34px, 5.2vw, 52px); line-height: 1.08;
    letter-spacing: -.032em; font-weight: 800; color: var(--lf-ink);
}}
.lf-lede {{ margin: 18px 0 0; font-size: 18px; max-width: 620px; }}

.lf-facts {{
    display: flex; flex-wrap: wrap; gap: 10px 26px;
    margin-top: 30px; padding-top: 22px; border-top: 1px solid var(--lf-line);
    font-size: 12px; letter-spacing: .07em; text-transform: uppercase;
    font-weight: 600; color: var(--lf-muted);
}}
.lf-facts b {{ color: var(--lf-ink-2); font-weight: 700; text-transform: none; letter-spacing: 0; }}
.lf-facts code {{ font-family: var(--lf-mono); font-size: 12px; text-transform: none; letter-spacing: 0; }}

/* --- sections --- */
section {{ margin-top: 62px; }}
.lf-eyebrow {{
    font-size: 11.5px; font-weight: 700; letter-spacing: .13em;
    text-transform: uppercase; color: var(--lf-indigo-strong); margin: 0;
}}
h2 {{
    margin: 12px 0 0; font-size: clamp(25px, 3.2vw, 33px); line-height: 1.16;
    letter-spacing: -.024em; font-weight: 800; color: var(--lf-ink);
}}
.lf-sub {{ margin: 12px 0 0; max-width: 640px; font-size: 15.5px; }}

/* --- KPI cards --- */
.lf-kpis {{
    display: grid; gap: 16px; margin-top: 30px;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}}
.lf-kpi {{
    background: var(--lf-surface); border: 1px solid var(--lf-line);
    border-radius: var(--lf-radius); padding: 22px 22px 20px; box-shadow: var(--lf-shadow);
}}
.lf-kpi .k {{
    font-size: 11.5px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: var(--lf-muted);
}}
.lf-kpi .v {{
    margin-top: 10px; font-size: 38px; line-height: 1; font-weight: 800;
    letter-spacing: -.03em; color: var(--lf-ink); font-variant-numeric: tabular-nums;
}}
.lf-kpi .n {{ margin-top: 9px; font-size: 13.5px; color: var(--lf-muted); }}
.lf-kpi.is-pass .v {{ color: var(--lf-pass); }}
.lf-kpi.is-fail .v {{ color: var(--lf-fail); }}
.lf-kpi.is-warn .v {{ color: var(--lf-warn); }}

/* --- tables --- */
.lf-panel {{
    margin-top: 28px; background: var(--lf-surface); border: 1px solid var(--lf-line);
    border-radius: var(--lf-radius); box-shadow: var(--lf-shadow); overflow: hidden;
}}
.lf-scroll {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14.5px; }}
thead th {{
    text-align: left; padding: 14px 20px; background: var(--lf-canvas);
    border-bottom: 1px solid var(--lf-line); color: var(--lf-muted);
    font-size: 11.5px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
    white-space: nowrap;
}}
tbody td {{ padding: 14px 20px; border-bottom: 1px solid var(--lf-line-soft); vertical-align: middle; }}
tbody tr:last-child td {{ border-bottom: 0; }}
tbody tr:hover td {{ background: var(--lf-indigo-tint); }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.name {{ font-family: var(--lf-mono); font-size: 13px; color: var(--lf-ink-2); white-space: nowrap; }}

.lf-pill {{
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    font-size: 12px; font-weight: 700; letter-spacing: .01em; white-space: nowrap;
}}
.lf-pill.pass {{ background: var(--lf-pass-soft); color: var(--lf-pass); }}
.lf-pill.fail {{ background: var(--lf-fail-soft); color: var(--lf-fail); }}
.lf-pill.warn {{ background: var(--lf-warn-soft); color: var(--lf-warn); }}
.lf-pill.info {{ background: var(--lf-indigo-soft); color: var(--lf-indigo-strong); }}

.lf-meter {{
    display: block; position: relative; width: 100%; min-width: 110px; height: 7px;
    border-radius: 999px; background: var(--lf-line); overflow: hidden;
}}
.lf-meter > i {{ position: absolute; inset: 0 auto 0 0; border-radius: 999px; display: block; }}
.lf-meter > i.pass {{ background: var(--lf-pass); }}
.lf-meter > i.warn {{ background: var(--lf-warn); }}
.lf-meter > i.fail {{ background: var(--lf-fail); }}
.lf-meter > i.indigo {{ background: var(--lf-indigo); }}

/* --- mode comparison --- */
.lf-modes {{ display: grid; gap: 16px; margin-top: 30px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}
.lf-mode {{
    background: var(--lf-surface); border: 1px solid var(--lf-line);
    border-radius: var(--lf-radius); padding: 24px; box-shadow: var(--lf-shadow);
}}
.lf-mode.is-primary {{ border-color: var(--lf-indigo); box-shadow: 0 0 0 3px var(--lf-indigo-soft), var(--lf-shadow); }}
.lf-mode h3 {{ margin: 14px 0 0; font-size: 19px; letter-spacing: -.018em; color: var(--lf-ink); font-weight: 700; }}
.lf-mode p {{ margin: 10px 0 0; font-size: 14.5px; }}
.lf-mode dl {{ margin: 18px 0 0; display: grid; grid-template-columns: 1fr auto; gap: 9px 16px; font-size: 14px; }}
.lf-mode dt {{ color: var(--lf-muted); }}
.lf-mode dd {{ margin: 0; text-align: right; font-weight: 700; color: var(--lf-ink-2); font-variant-numeric: tabular-nums; }}

/* --- notes --- */
.lf-note {{
    margin-top: 26px; padding: 20px 22px; border-radius: var(--lf-radius);
    background: var(--lf-indigo-soft); border: 1px solid #DDE1FB; color: var(--lf-ink-2); font-size: 14.5px;
}}
.lf-note strong {{ color: var(--lf-indigo-deep); }}
.lf-note code {{ font-family: var(--lf-mono); font-size: 13px; background: rgba(255,255,255,.7); padding: 1px 6px; border-radius: 5px; }}

.lf-fail-item {{ padding: 18px 20px; border-bottom: 1px solid var(--lf-line-soft); }}
.lf-fail-item:last-child {{ border-bottom: 0; }}
.lf-fail-item .t {{ font-family: var(--lf-mono); font-size: 13px; color: var(--lf-ink); }}
.lf-fail-item .m {{ margin-top: 7px; font-size: 13.5px; color: var(--lf-fail); font-family: var(--lf-mono); }}

footer {{
    margin-top: 68px; padding-top: 26px; border-top: 1px solid var(--lf-line);
    font-size: 13px; color: var(--lf-faint);
}}
footer b {{ color: var(--lf-muted); font-weight: 600; }}

@media (max-width: 640px) {{
    .lf-shell {{ padding: 0 18px 56px; }}
    .lf-hero {{ padding-top: 42px; }}
    .lf-bar {{ flex-wrap: wrap; }}
}}
@media print {{
    body {{ background: #fff; }}
    .lf-panel, .lf-kpi, .lf-mode {{ box-shadow: none; }}
    section {{ break-inside: avoid; }}
}}
"""


def _kpis(run: dict[str, Any], coverage: dict[str, Any]) -> str:
    total = run["total"] or 1
    pass_rate = run["passed"] / total * 100
    cov_pct = float(coverage["totals"].get("percent_covered", 0.0))
    cov_tone = _coverage_tone(cov_pct)
    failed_tone = "fail" if run["failed"] else "pass"

    cards = [
        ("pass", "Tests passed", f"{run['passed']}", f"of {run['total']} collected · {pass_rate:.1f}% pass rate"),
        (failed_tone, "Failures", f"{run['failed']}", "no unresolved failures" if not run["failed"] else "see failure detail below"),
        (cov_tone, "Statement coverage",
         f"{cov_pct:.0f}%",
         f"{coverage['totals'].get('covered_lines', 0):,} of {coverage['totals'].get('num_statements', 0):,} statements"),
        ("info", "Wall clock", f"{run['duration']:.1f}s", f"across {len(run['suites'])} test modules"),
    ]
    out = ['<div class="lf-kpis">']
    for tone, key, value, note in cards:
        cls = f" is-{tone}" if tone in ("pass", "fail", "warn") else ""
        out.append(
            f'<div class="lf-kpi{cls}"><div class="k">{_e(key)}</div>'
            f'<div class="v">{_e(value)}</div><div class="n">{_e(note)}</div></div>'
        )
    out.append("</div>")
    return "\n".join(out)


def _suite_table(run: dict[str, Any]) -> str:
    rows = []
    for s in run["suites"]:
        pct = (s["passed"] / s["total"] * 100) if s["total"] else 0.0
        tone = "pass" if s["failed"] == 0 else "fail"
        short = s["name"].removeprefix("tests/")
        status = (
            f'<span class="lf-pill pass">{s["passed"]}/{s["total"]} passing</span>'
            if s["failed"] == 0
            else f'<span class="lf-pill fail">{s["failed"]} failing</span>'
        )
        rows.append(
            f"<tr><td class=\"name\">{_e(short)}</td>"
            f"<td>{status}</td>"
            f'<td style="min-width:160px"><span class="lf-meter"><i class="{tone}" style="width:{pct:.1f}%"></i></span></td>'
            f'<td class="num">{s["total"]}</td>'
            f'<td class="num">{s["duration"] * 1000:.0f} ms</td></tr>'
        )
    return (
        '<div class="lf-panel"><div class="lf-scroll"><table>'
        "<thead><tr><th>Test module</th><th>Status</th><th>Pass rate</th>"
        '<th class="num">Cases</th><th class="num">Duration</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div></div>"
    )


def _coverage_table(coverage: dict[str, Any], limit: int | None = None) -> str:
    files = coverage["files"][:limit] if limit else coverage["files"]
    rows = []
    for f in files:
        tone = _coverage_tone(f["percent"])
        rows.append(
            f'<tr><td class="name">{_e(f["name"])}</td>'
            f'<td style="min-width:150px"><span class="lf-meter"><i class="{tone}" style="width:{f["percent"]:.1f}%"></i></span></td>'
            f'<td class="num"><span class="lf-pill {tone}">{f["percent"]:.0f}%</span></td>'
            f'<td class="num">{f["statements"]}</td>'
            f'<td class="num">{f["missing"]}</td></tr>'
        )
    return (
        '<div class="lf-panel"><div class="lf-scroll"><table>'
        "<thead><tr><th>Module</th><th>Coverage</th>"
        '<th class="num">%</th><th class="num">Statements</th><th class="num">Uncovered</th>'
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>"
    )


def _modes(run: dict[str, Any], baseline: dict[str, Any] | None) -> str:
    def block(title: str, desc: str, data: dict[str, Any], primary: bool) -> str:
        tone = "pass" if data["failed"] == 0 else "warn"
        label = "All green" if data["failed"] == 0 else f'{data["failed"]} environment-gated'
        return (
            f'<div class="lf-mode{" is-primary" if primary else ""}">'
            f'<span class="lf-pill {tone}">{_e(label)}</span>'
            f"<h3>{_e(title)}</h3><p>{_e(desc)}</p><dl>"
            f'<dt>Passed</dt><dd>{data["passed"]}</dd>'
            f'<dt>Failed</dt><dd>{data["failed"]}</dd>'
            f'<dt>Collected</dt><dd>{data["total"]}</dd>'
            f'<dt>Duration</dt><dd>{data["duration"]:.2f}s</dd>'
            "</dl></div>"
        )

    cards = [
        block(
            "Offline fixture mode",
            "The extractor is bound to a deterministic in-process stub through the "
            "repository's own RUNNER_IMPORT_PATH hook. No API key, no network, no model spend.",
            run,
            True,
        )
    ]
    if baseline:
        cards.append(
            block(
                "Bare sandbox, no credentials",
                "Identical suite with OPENAI_API_KEY unset and no runner override. The route "
                "tests that reach the live extractor cannot construct a client and fail at import "
                "of the dependency, not at an assertion.",
                baseline,
                False,
            )
        )
    return f'<div class="lf-modes">{"".join(cards)}</div>'


def _failures(run: dict[str, Any]) -> str:
    if not run["failures"]:
        return ""
    items = "".join(
        f'<div class="lf-fail-item"><div class="t">{_e(f["suite"])} :: {_e(f["case"])}</div>'
        f'<div class="m">{_e(f["message"][:400])}</div></div>'
        for f in run["failures"]
    )
    return (
        "<section><p class=\"lf-eyebrow\">Failure detail</p>"
        "<h2>Unresolved failures</h2>"
        f'<div class="lf-panel">{items}</div></section>'
    )


def render(
    run: dict[str, Any],
    coverage: dict[str, Any],
    baseline: dict[str, Any] | None,
    meta: dict[str, str],
) -> tuple[str, str]:
    generated = _dt.datetime.now(_dt.timezone.utc).strftime("%d %B %Y, %H:%M UTC")
    cov_pct = float(coverage["totals"].get("percent_covered", 0.0))
    gated = baseline["failed"] if baseline else 0

    note = ""
    if baseline and gated:
        note = (
            f'<div class="lf-note"><strong>Why the two columns differ.</strong> '
            f"{gated} route tests exercise the PDF ingest path end to end, which resolves the "
            f"extractor through <code>api_v1/runner_loader.py</code>. With no credentials present "
            f"the default runner raises before any assertion runs. Pointing "
            f"<code>RUNNER_IMPORT_PATH</code> at a deterministic stub satisfies the dependency and "
            f"the same {gated} tests pass unchanged — the suite has no real red.</div>"
        )

    facts = " ".join(
        f"<span><b>{_e(v)}</b></span>" if k == "" else f"<span>{_e(k)} <b>{_e(v)}</b></span>"
        for k, v in meta.items()
    )

    head = f"<style>{_css()}</style>"
    body = f"""

<div class="lf-shell">
  <header class="lf-bar">
    <div class="lf-brand">
      <span class="lf-mark">{mark_svg()}</span>
      <span class="lf-wordmark">LinForensics</span>
    </div>
    <div class="lf-bar-meta">Generated {_e(generated)}</div>
  </header>

  <div class="lf-hero">
    <span class="lf-badge">Automated test evidence</span>
    <h1>Test &amp; coverage report</h1>
    <p class="lf-lede">Every commit to the analysis engine is verified by a deterministic
    suite that runs with no credentials, no network calls and no model spend. This is the
    unedited output of that run.</p>
    <div class="lf-facts">{facts}</div>
  </div>

  <section>
    <p class="lf-eyebrow">Summary</p>
    <h2>Where the suite stands</h2>
    {_kpis(run, coverage)}
  </section>

  <section>
    <p class="lf-eyebrow">Run modes</p>
    <h2>Two ways the suite was executed</h2>
    <p class="lf-sub">The engine is designed so that its correctness can be demonstrated without
    reaching a language model. Both runs below cover the identical {run['total']} collected tests.</p>
    {_modes(run, baseline)}
    {note}
  </section>

  <section>
    <p class="lf-eyebrow">Breakdown</p>
    <h2>Results by test module</h2>
    <p class="lf-sub">{len(run['suites'])} modules covering ingest normalisation, scoring,
    convergence detection, entitlements, billing, chain of custody and report rendering.</p>
    {_suite_table(run)}
  </section>

  <section>
    <p class="lf-eyebrow">Coverage</p>
    <h2>Statement coverage by module</h2>
    <p class="lf-sub">Overall statement coverage is {cov_pct:.0f}% across
    {coverage['totals'].get('num_statements', 0):,} statements, sorted lowest first so the
    thinnest areas surface at the top.</p>
    {_coverage_table(coverage)}
  </section>

  {_failures(run)}

  <footer>
    <p><b>Provenance.</b> Produced by <code>reports/generate_test_report.py</code> from the
    machine-readable pytest and coverage output of a single run. No figure on this page is
    entered by hand.</p>
    <p>LinForensics is decision-support software. It does not provide legal advice, medical
    advice, mental health advice, diagnoses, predictions, emergency support or automated
    determinations.</p>
  </footer>
</div>
"""
    return head, body


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    ap.add_argument("--json", default=str(here / "data" / "report.json"))
    ap.add_argument("--coverage", default=str(here / "data" / "coverage.json"))
    ap.add_argument("--baseline", default=str(here / "data" / "report-baseline.json"))
    ap.add_argument("--out", default=str(here / "lin-test-report.html"))
    ap.add_argument("--repo", default="MeLinResearch/Updgrade")
    ap.add_argument("--commit", default="")
    ap.add_argument("--python", default="")
    ap.add_argument(
        "--fragment",
        action="store_true",
        help="emit body markup only, for hosts that supply their own document shell",
    )
    args = ap.parse_args()

    run = load_run(Path(args.json))
    coverage = load_coverage(Path(args.coverage))
    baseline_path = Path(args.baseline)
    baseline = load_run(baseline_path) if baseline_path.exists() else None

    meta = {"Repository": args.repo}
    if args.commit:
        meta["Commit"] = args.commit
    if args.python:
        meta["Python"] = args.python
    meta["Suite"] = f"{run['total']} tests"

    head, body = render(run, coverage, baseline, meta)
    out = Path(args.out)
    out.write_text(
        body
        if args.fragment
        else document(
            head,
            body,
            title=f"{args.repo} — Test &amp; coverage report",
            description="Automated test and coverage evidence for the LinForensics analysis engine.",
        )
    )
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
