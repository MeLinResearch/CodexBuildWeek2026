#!/usr/bin/env python3
"""Render the customer-facing LinForensics report, plain or annotated.

Reads the bundle produced by ``build_sample_case.py`` — real output from the
shipping analysis engine — and renders it as the document a paying customer
receives. In ``--mode annotated`` the same document is placed on a stage with
callout boxes and drawn arrows explaining each part in plain language, for use
as a "what you get" panel on liforensics.com.

Usage:
    python reports/generate_sample_report.py --mode plain
    python reports/generate_sample_report.py --mode annotated
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from lf_theme import LEVEL_TONE, document, mark_svg, tokens_css


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _pretty_time(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M")
    except (ValueError, AttributeError):
        return iso


# --- the callouts, in reading order --------------------------------------
CALLOUTS = [
    {
        "anchor": "a-level",
        "side": "left",
        "title": "One plain-English level",
        "text": "No score, no verdict, no diagnosis. Just where this conversation sits on a "
                "four-level scale, in words anyone can act on.",
    },
    {
        "anchor": "a-prov",
        "side": "right",
        "title": "Stamped so it can be checked",
        "text": "The exact file you uploaded, when it arrived, and the version of the analysis "
                "that ran. Two people running the same file get the same report.",
    },
    {
        "anchor": "a-group",
        "side": "left",
        "title": "Grouped in everyday language",
        "text": "Findings are sorted into categories you can read out loud — pressure, "
                "restriction, consequence language — not clinical or internal codes.",
    },
    {
        "anchor": "a-quote",
        "side": "right",
        "title": "Every finding quotes your own file",
        "text": "Each line is a direct excerpt from the text you submitted. Nothing is "
                "paraphrased, summarised or invented.",
    },
    {
        "anchor": "a-meta",
        "side": "left",
        "title": "You can find it in the original",
        "text": "Who said it and when travels with every excerpt, so you can locate the same "
                "line in your own export in seconds.",
    },
    {
        "anchor": "a-steps",
        "side": "right",
        "title": "Practical next steps",
        "text": "Concrete, non-alarming actions matched to the level found — what to do next, "
                "not what to conclude.",
    },
    {
        "anchor": "a-limits",
        "side": "left",
        "title": "Clear about what it is not",
        "text": "Stated limits and a plain disclaimer on every report. This is decision-support "
                "for you or a qualified professional to review — never an automated determination.",
    },
]


def _css(annotated: bool) -> str:
    base = f"""
:root {{
    color-scheme: light;
{tokens_css()}
    --lf-radius: 14px;
    --lf-shadow: 0 1px 2px rgba(15, 23, 42, .04), 0 12px 32px -18px rgba(15, 23, 42, .28);
    --lf-doc-shadow: 0 1px 3px rgba(15, 23, 42, .05), 0 28px 60px -28px rgba(15, 23, 42, .34);
}}
* {{ box-sizing: border-box; }}
body {{
    margin: 0; font-family: var(--lf-font); font-size: 16px; line-height: 1.6;
    color: var(--lf-body);
    background:
        radial-gradient(1100px 480px at 14% -10%, var(--lf-indigo-tint) 0%, rgba(245,246,255,0) 60%),
        linear-gradient(180deg, var(--lf-surface) 0%, var(--lf-canvas) 100%);
    background-attachment: fixed;
    -webkit-font-smoothing: antialiased;
}}
.lf-shell {{ max-width: 1240px; margin: 0 auto; padding: 0 28px 84px; }}

/* masthead */
.lf-bar {{
    display: flex; align-items: center; justify-content: space-between; gap: 20px;
    padding: 22px 0 20px; border-bottom: 1px solid var(--lf-line);
}}
.lf-brand {{ display: flex; align-items: center; gap: 11px; }}
.lf-mark {{
    width: 30px; height: 30px; border-radius: 9px; flex: none; display: grid; place-items: center;
    background: linear-gradient(160deg, var(--lf-indigo) 0%, var(--lf-indigo-deep) 100%);
}}
.lf-wordmark {{ font-weight: 700; font-size: 17px; letter-spacing: -.015em; color: var(--lf-ink); }}
.lf-bar-meta {{ font-size: 13px; color: var(--lf-muted); }}

/* intro */
.lf-intro {{ padding: 58px 0 8px; max-width: 720px; }}
.lf-badge {{
    display: inline-block; padding: 6px 14px; border-radius: 999px;
    background: var(--lf-indigo-soft); color: var(--lf-indigo-strong);
    font-size: 11.5px; font-weight: 700; letter-spacing: .11em; text-transform: uppercase;
}}
h1 {{
    margin: 22px 0 0; font-size: clamp(33px, 5vw, 50px); line-height: 1.08;
    letter-spacing: -.032em; font-weight: 800; color: var(--lf-ink);
}}
.lf-lede {{ margin: 18px 0 0; font-size: 18px; max-width: 640px; }}

/* --- the report document --- */
.lf-doc {{
    background: var(--lf-surface); border: 1px solid var(--lf-line);
    border-radius: 18px; box-shadow: var(--lf-doc-shadow); overflow: hidden;
}}
.lf-doc-head {{
    display: flex; align-items: flex-start; justify-content: space-between; gap: 20px;
    padding: 26px 32px; border-bottom: 1px solid var(--lf-line); background: var(--lf-surface);
}}
.lf-doc-title {{ font-size: 19px; font-weight: 800; letter-spacing: -.02em; color: var(--lf-ink); }}
.lf-doc-sub {{ margin-top: 4px; font-size: 13px; color: var(--lf-muted); }}
.lf-doc-ref {{
    text-align: right; font-family: var(--lf-mono); font-size: 12px;
    color: var(--lf-muted); line-height: 1.7; white-space: nowrap;
}}
.lf-doc-body {{ padding: 30px 32px 34px; }}
.lf-doc h3 {{
    margin: 0 0 4px; font-size: 11.5px; font-weight: 700; letter-spacing: .12em;
    text-transform: uppercase; color: var(--lf-indigo-strong);
}}
.lf-block + .lf-block {{ margin-top: 30px; padding-top: 30px; border-top: 1px solid var(--lf-line-soft); }}

/* level band */
.lf-level {{
    display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
    padding: 20px 22px; border-radius: var(--lf-radius);
    background: var(--lf-warn-soft); border: 1px solid var(--lf-warn-line);
}}
.lf-level.tone-fail {{ background: var(--lf-fail-soft); border-color: var(--lf-fail-line); }}
.lf-level.tone-pass {{ background: var(--lf-pass-soft); border-color: #CDEBE0; }}
.lf-level.tone-muted {{ background: var(--lf-canvas); border-color: var(--lf-line); }}
.lf-level-dot {{ width: 11px; height: 11px; border-radius: 50%; background: var(--lf-warn); flex: none; }}
.lf-level.tone-fail .lf-level-dot {{ background: var(--lf-fail); }}
.lf-level.tone-pass .lf-level-dot {{ background: var(--lf-pass); }}
.lf-level.tone-muted .lf-level-dot {{ background: var(--lf-faint); }}
.lf-level-name {{
    font-size: 23px; font-weight: 800; letter-spacing: -.022em; color: var(--lf-ink); line-height: 1.2;
}}
.lf-level-tag {{
    margin-left: auto; padding: 5px 12px; border-radius: 999px; background: rgba(255,255,255,.75);
    font-size: 12px; font-weight: 700; color: var(--lf-ink-2); white-space: nowrap;
}}
.lf-summary {{ margin: 16px 0 0; font-size: 16px; color: var(--lf-ink-2); max-width: 62ch; }}

/* provenance */
.lf-prov {{
    display: grid; gap: 14px 26px; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    padding: 18px 20px; border: 1px dashed var(--lf-line); border-radius: var(--lf-radius);
    background: var(--lf-canvas);
}}
.lf-prov dt {{
    font-size: 10.5px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: var(--lf-muted);
}}
.lf-prov dd {{
    margin: 5px 0 0; font-family: var(--lf-mono); font-size: 12.5px;
    color: var(--lf-ink-2); word-break: break-word;
}}

/* pattern groups */
.lf-group + .lf-group {{ margin-top: 22px; }}
.lf-group-name {{ font-size: 17px; font-weight: 700; letter-spacing: -.015em; color: var(--lf-ink); }}
.lf-group-desc {{ margin: 5px 0 0; font-size: 14.5px; color: var(--lf-muted); max-width: 64ch; }}
.lf-group-count {{
    display: inline-block; margin-left: 9px; padding: 2px 9px; border-radius: 999px;
    background: var(--lf-indigo-soft); color: var(--lf-indigo-strong);
    font-size: 11.5px; font-weight: 700; vertical-align: 2px;
}}
.lf-quotes {{ margin: 15px 0 0; padding: 0; list-style: none; }}
.lf-quotes li {{
    padding: 13px 16px; border-left: 3px solid var(--lf-indigo);
    background: var(--lf-indigo-tint); border-radius: 0 10px 10px 0;
}}
.lf-quotes li + li {{ margin-top: 9px; }}
.lf-quote {{ font-size: 15px; color: var(--lf-ink); }}
.lf-quote-meta {{
    margin-top: 7px; font-size: 12px; color: var(--lf-muted);
    display: flex; flex-wrap: wrap; gap: 4px 14px;
}}
.lf-quote-meta code {{ font-family: var(--lf-mono); font-size: 11.5px; }}

/* steps + limits */
.lf-steps {{ margin: 14px 0 0; padding: 0; list-style: none; counter-reset: step; }}
.lf-steps li {{
    position: relative; padding-left: 34px; font-size: 15.5px; color: var(--lf-ink-2);
    counter-increment: step;
}}
.lf-steps li + li {{ margin-top: 11px; }}
.lf-steps li::before {{
    content: counter(step); position: absolute; left: 0; top: 1px;
    width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center;
    background: var(--lf-indigo-soft); color: var(--lf-indigo-strong);
    font-size: 12px; font-weight: 700;
}}
.lf-limits {{ margin: 14px 0 0; padding-left: 20px; font-size: 14.5px; }}
.lf-limits li + li {{ margin-top: 7px; }}
.lf-disclaimer {{
    margin: 18px 0 0; padding: 16px 18px; border-radius: var(--lf-radius);
    background: var(--lf-canvas); border: 1px solid var(--lf-line);
    font-size: 13.5px; color: var(--lf-muted);
}}
footer {{
    margin-top: 60px; padding-top: 24px; border-top: 1px solid var(--lf-line);
    font-size: 13px; color: var(--lf-faint);
}}
@media (max-width: 720px) {{
    .lf-shell {{ padding: 0 16px 60px; }}
    .lf-doc-head, .lf-doc-body {{ padding-left: 20px; padding-right: 20px; }}
    .lf-doc-head {{ flex-direction: column; }}
    .lf-doc-ref {{ text-align: left; }}
}}
@media print {{
    body {{ background: #fff; }}
    .lf-doc {{ box-shadow: none; }}
}}
"""
    if not annotated:
        return base + "\n.lf-stage { max-width: 860px; margin: 40px auto 0; }\n"

    return base + """
/* --- annotation stage --- */
.lf-stage { position: relative; margin-top: 46px; }
.lf-stage-doc { max-width: 620px; margin: 0 auto; }
.lf-wires { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1; }
.lf-callout {
    background: var(--lf-surface); border: 1px solid var(--lf-indigo-line);
    border-radius: var(--lf-radius); padding: 16px 18px; box-shadow: var(--lf-shadow);
    z-index: 2;
}
.lf-callout .n {
    display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 50%;
    background: var(--lf-indigo); color: #fff; font-size: 12px; font-weight: 700;
    margin-bottom: 9px;
}
.lf-callout h4 {
    margin: 0 0 6px; font-size: 15px; font-weight: 700; letter-spacing: -.012em; color: var(--lf-ink);
}
.lf-callout p { margin: 0; font-size: 13.5px; line-height: 1.55; color: var(--lf-body); }

/* the little numbered pin sitting on the document */
.lf-pin {
    display: inline-grid; place-items: center; width: 20px; height: 20px; border-radius: 50%;
    background: var(--lf-indigo); color: #fff; font-size: 11px; font-weight: 700;
    letter-spacing: 0; vertical-align: -5px; margin-right: 8px; flex: none;
}
.lf-quote-meta .lf-pin { vertical-align: -6px; }

/* wide: absolute columns either side, arrows drawn between */
@media (min-width: 1080px) {
    .lf-callout { position: absolute; width: 268px; }
    .lf-callout[data-side="left"]  { left: 0; }
    .lf-callout[data-side="right"] { right: 0; }
}
/* narrow: stack the explanations under the document, no arrows */
@media (max-width: 1079px) {
    .lf-wires { display: none; }
    .lf-notes { display: grid; gap: 14px; margin-top: 30px;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
    .lf-callout { position: static !important; width: auto !important; }
}
@media (min-width: 1080px) { .lf-notes { display: contents; } }
@media print { .lf-wires, .lf-callout { display: none; } }
"""


# --- document markup ------------------------------------------------------

def _pin(n: int, annotated: bool) -> str:
    return f'<span class="lf-pin">{n}</span>' if annotated else ""


def render_doc(bundle: dict, annotated: bool) -> str:
    public = bundle["public_report"]
    user = bundle["user_report"]
    case = bundle["case_result"]
    prov = case.get("provenance") or {}

    level = public["summary"]["overall_level"]
    tone = LEVEL_TONE.get(level.lower(), "warn")
    total_findings = sum(len(g["examples"]) for g in public["pattern_groups"])

    pins = {c["anchor"]: i + 1 for i, c in enumerate(CALLOUTS)}

    def pin(anchor: str) -> str:
        return _pin(pins[anchor], annotated)

    # provenance strip
    prov_rows = [
        ("Source file", prov.get("source_filename", "—")),
        ("Received", _pretty_time(prov.get("upload_time", ""))),
        ("Analysis run", prov.get("analysis_run_id", "—")),
        ("Engine version", prov.get("scoring_version") or prov.get("model_used") or "TAS-v1.1"),
    ]
    prov_html = "".join(
        f"<div><dt>{_e(k)}</dt><dd>{_e(v)}</dd></div>" for k, v in prov_rows
    )

    # pattern groups
    groups = []
    for gi, group in enumerate(public["pattern_groups"]):
        quotes = []
        for qi, ex in enumerate(group["examples"]):
            meta_bits = []
            if ex.get("speaker_label"):
                meta_bits.append(f'<span>{_e(ex["speaker_label"])}</span>')
            if ex.get("timestamp"):
                meta_bits.append(f'<span>{_e(_pretty_time(ex["timestamp"]))}</span>')
            if ex.get("message_id"):
                meta_bits.append(f'<span>message <code>{_e(ex["message_id"])}</code></span>')
            first = gi == 0 and qi == 0
            last_of_first = gi == 0 and qi == len(group["examples"]) - 1
            q_id = ' id="a-quote"' if first else ""
            m_id = ' id="a-meta"' if last_of_first else ""
            q_pin = pin("a-quote") if first else ""
            m_pin = pin("a-meta") if last_of_first else ""
            quotes.append(
                f"<li><div class=\"lf-quote\"{q_id}>{q_pin}&ldquo;{_e(ex['quote_text'])}&rdquo;</div>"
                f"<div class=\"lf-quote-meta\"{m_id}>{m_pin}{''.join(meta_bits)}</div></li>"
            )
        g_id = ' id="a-group"' if gi == 0 else ""
        g_pin = pin("a-group") if gi == 0 else ""
        groups.append(
            f'<div class="lf-group"><div class="lf-group-name"{g_id}>{g_pin}'
            f'{_e(group["public_category"])}'
            f'<span class="lf-group-count">{len(group["examples"])}</span></div>'
            f'<p class="lf-group-desc">{_e(group["description"])}</p>'
            f'<ul class="lf-quotes">{"".join(quotes)}</ul></div>'
        )

    steps = "".join(f"<li>{_e(s)}</li>" for s in user.get("next_steps", []))
    limits = "".join(f"<li>{_e(l)}</li>" for l in public["limitations"])

    return f"""
<article class="lf-doc">
  <div class="lf-doc-head">
    <div>
      <div class="lf-brand" style="margin-bottom:12px">
        <span class="lf-mark">{mark_svg()}</span>
        <span class="lf-wordmark">LinForensics</span>
      </div>
      <div class="lf-doc-title">Communication pattern review</div>
      <div class="lf-doc-sub">Structured report prepared for independent human review</div>
    </div>
    <div class="lf-doc-ref">
      Case&nbsp;LF-2026-0184<br>
      {_e(_pretty_time(prov.get("upload_time", "")))}<br>
      {_e(public["version"])}
    </div>
  </div>

  <div class="lf-doc-body">
    <div class="lf-block">
      <h3>Overall assessment</h3>
      <div class="lf-level tone-{tone}" id="a-level">
        {pin("a-level")}<span class="lf-level-dot"></span>
        <span class="lf-level-name">{_e(level)}</span>
        <span class="lf-level-tag">Human review required</span>
      </div>
      <p class="lf-summary">{_e(public["summary"]["plain_language_summary"])}</p>
    </div>

    <div class="lf-block">
      <h3>{pin("a-prov")}Provenance</h3>
      <dl class="lf-prov" id="a-prov">{prov_html}</dl>
    </div>

    <div class="lf-block">
      <h3>Patterns identified &middot; {total_findings} cited excerpts</h3>
      {"".join(groups)}
    </div>

    <div class="lf-block">
      <h3>{pin("a-steps")}Suggested next steps</h3>
      <ol class="lf-steps" id="a-steps">{steps}</ol>
    </div>

    <div class="lf-block" id="a-limits">
      <h3>{pin("a-limits")}Limitations &amp; disclaimer</h3>
      <ul class="lf-limits">{limits}</ul>
      <p class="lf-disclaimer">{_e(public["disclaimer"])}</p>
    </div>
  </div>
</article>
"""


def _callouts_html() -> str:
    items = []
    for i, c in enumerate(CALLOUTS, start=1):
        items.append(
            f'<aside class="lf-callout" data-anchor="{c["anchor"]}" data-side="{c["side"]}">'
            f'<span class="n">{i}</span>'
            f'<h4>{_e(c["title"])}</h4><p>{_e(c["text"])}</p></aside>'
        )
    return f'<div class="lf-notes">{"".join(items)}</div>'


_WIRE_JS = """
(function () {
  var stage = document.querySelector('.lf-stage');
  var svg = document.querySelector('.lf-wires');
  if (!stage || !svg) return;
  var wide = window.matchMedia('(min-width: 1080px)');
  var callouts = Array.prototype.slice.call(document.querySelectorAll('.lf-callout'));

  function layout() {
    svg.innerHTML = '';
    callouts.forEach(function (c) { c.style.top = ''; });
    if (!wide.matches) { stage.style.height = ''; return; }

    var stageBox = stage.getBoundingClientRect();
    var doc = stage.querySelector('.lf-stage-doc');
    var docBox = doc.getBoundingClientRect();

    // 1. desired vertical position: centre each callout on its anchor
    var placed = { left: [], right: [] };
    callouts.forEach(function (c) {
      var anchor = document.getElementById(c.dataset.anchor);
      if (!anchor) return;
      var box = anchor.getBoundingClientRect();
      var want = box.top + box.height / 2 - stageBox.top - c.offsetHeight / 2;
      placed[c.dataset.side].push({ el: c, anchor: anchor, top: Math.max(0, want) });
    });

    // 2. push overlapping callouts down within their column
    var GAP = 18;
    Object.keys(placed).forEach(function (side) {
      var col = placed[side].sort(function (a, b) { return a.top - b.top; });
      for (var i = 1; i < col.length; i++) {
        var min = col[i - 1].top + col[i - 1].el.offsetHeight + GAP;
        if (col[i].top < min) col[i].top = min;
      }
      col.forEach(function (item) { item.el.style.top = item.top + 'px'; });
    });

    // 3. size the stage to whichever column runs longest
    var lowest = docBox.height;
    callouts.forEach(function (c) {
      lowest = Math.max(lowest, (parseFloat(c.style.top) || 0) + c.offsetHeight);
    });
    stage.style.height = lowest + 'px';
    svg.setAttribute('viewBox', '0 0 ' + stageBox.width + ' ' + lowest);

    // 4. draw one curved connector per callout
    var ns = 'http://www.w3.org/2000/svg';
    var defs = document.createElementNS(ns, 'defs');
    defs.innerHTML =
      '<marker id="lf-arrow" markerWidth="7" markerHeight="7" refX="5.4" refY="3" orient="auto">' +
      '<path d="M0.4 0.5 L5.8 3 L0.4 5.5 z" fill="var(--lf-indigo)"/></marker>';
    svg.appendChild(defs);

    ['left', 'right'].forEach(function (side) {
      placed[side].forEach(function (item) {
        var c = item.el.getBoundingClientRect();
        var a = item.anchor.getBoundingClientRect();
        var fromX = (side === 'left' ? c.right : c.left) - stageBox.left;
        var fromY = c.top + c.height / 2 - stageBox.top;
        var toX = (side === 'left' ? a.left - 9 : a.right + 9) - stageBox.left;
        var toY = a.top + Math.min(a.height / 2, 22) - stageBox.top;
        var mid = (fromX + toX) / 2;

        var path = document.createElementNS(ns, 'path');
        path.setAttribute('d', 'M ' + fromX + ' ' + fromY +
                               ' C ' + mid + ' ' + fromY + ', ' + mid + ' ' + toY +
                               ', ' + toX + ' ' + toY);
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', 'var(--lf-indigo)');
        path.setAttribute('stroke-width', '1.6');
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('opacity', '.6');
        path.setAttribute('marker-end', 'url(#lf-arrow)');
        svg.appendChild(path);

        var dot = document.createElementNS(ns, 'circle');
        dot.setAttribute('cx', fromX); dot.setAttribute('cy', fromY); dot.setAttribute('r', '3');
        dot.setAttribute('fill', 'var(--lf-indigo)');
        svg.appendChild(dot);
      });
    });
  }

  if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout);
  window.addEventListener('load', layout);
  window.addEventListener('resize', layout);
  if (window.ResizeObserver) new ResizeObserver(layout).observe(stage);
  layout();
})();
"""


def render(bundle: dict, annotated: bool) -> tuple[str, str]:
    doc = render_doc(bundle, annotated)
    generated = datetime.now().strftime("%d %B %Y")

    if annotated:
        stage = (
            '<div class="lf-stage">'
            '<svg class="lf-wires" aria-hidden="true" preserveAspectRatio="none"></svg>'
            f'<div class="lf-stage-doc">{doc}</div>'
            f"{_callouts_html()}"
            "</div>"
            f"<script>{_WIRE_JS}</script>"
        )
        badge, title, lede = (
            "What you receive",
            "Inside a LinForensics report",
            "This is a complete sample report, produced by the same analysis engine that runs on "
            "your file. The notes around it explain what each part is and why it is there.",
        )
    else:
        stage = f'<div class="lf-stage">{doc}</div>'
        badge, title, lede = (
            "Sample deliverable",
            "Sample report",
            "A complete example of the report produced for a submitted conversation. The content "
            "below is synthetic; the structure, wording and analysis are the live product.",
        )

    body = f"""
<div class="lf-shell">
  <header class="lf-bar">
    <div class="lf-brand">
      <span class="lf-mark">{mark_svg()}</span>
      <span class="lf-wordmark">LinForensics</span>
    </div>
    <div class="lf-bar-meta">Sample &middot; {_e(generated)}</div>
  </header>

  <div class="lf-intro">
    <span class="lf-badge">{_e(badge)}</span>
    <h1>{_e(title)}</h1>
    <p class="lf-lede">{_e(lede)}</p>
  </div>

  {stage}

  <footer>
    <p>Sample content is synthetic and does not describe any real person or conversation.
    LinForensics is decision-support software. It does not provide legal advice, medical advice,
    mental health advice, diagnoses, predictions, emergency support or automated determinations.</p>
  </footer>
</div>
"""
    return f"<style>{_css(annotated)}</style>", body


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", default=str(here / "data" / "sample_case.json"))
    ap.add_argument("--mode", choices=("plain", "annotated"), default="annotated")
    ap.add_argument("--out", default="")
    ap.add_argument("--fragment", action="store_true",
                    help="emit body markup only, for embedding in an existing page")
    args = ap.parse_args()

    bundle = json.loads(Path(args.bundle).read_text())
    annotated = args.mode == "annotated"
    head, body = render(bundle, annotated)

    out = Path(args.out) if args.out else here / (
        "sample-report-annotated.html" if annotated else "sample-report.html"
    )
    title = "Inside a LinForensics report" if annotated else "LinForensics sample report"
    out.write_text(body if args.fragment else document(
        head, body, title=title,
        description="An annotated example of the communication pattern report LinForensics produces."
        if annotated else "A complete example of a LinForensics communication pattern report.",
    ))
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
