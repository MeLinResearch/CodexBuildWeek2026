#!/usr/bin/env python3
"""Produce a sample LinForensics case result using the real analysis engine.

The transcript and the extractor candidates below are synthetic, but everything
downstream of them — span validation, severity assignment, scoring, tiering,
boundary and convergence detection, and both report renderers — is the shipping
engine. That keeps the marketing sample honest: it is the same object a paying
customer receives, not a mock-up.

Usage:
    python reports/build_sample_case.py --engine-root /path/to/updgrade \
        --out reports/data/sample_case.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VERSIONS = {
    "taxonomy_version": "LIN-TAXONOMY-v0.6",
    "scoring_spec_version": "TAS-v1.1",
    "severity_table_version": "severity-table-v1.0",
    "boundary_detector_version": "boundary-detector-v1.0",
    "override_flags_version": "override-flags-v1.0",
}

THREAD = "lf-2026-0184"
COUNTERPARTY = "Contact (unverified)"
CLIENT = "Submitting party"

# --- synthetic transcript -------------------------------------------------
MESSAGES = [
    ("m01", "2026-02-11T20:14:00+00:00", "sp-a", COUNTERPARTY,
     "I know we only started talking last week but I have never felt this "
     "connected to anyone. You are my soulmate, I am certain of it."),
    ("m02", "2026-02-11T20:31:00+00:00", "sp-b", CLIENT,
     "That's a lot, honestly. I'd rather take this slowly."),
    ("m03", "2026-02-12T23:47:00+00:00", "sp-a", COUNTERPARTY,
     "I run a private commodities desk in Geneva and I clear more in a quarter "
     "than most people see in a decade. I am telling you this because I want to "
     "take care of you."),
    ("m04", "2026-02-14T01:12:00+00:00", "sp-a", COUNTERPARTY,
     "Please don't tell your friends about us yet. They will talk you out of it "
     "and they don't understand what we have."),
    ("m05", "2026-02-14T01:20:00+00:00", "sp-b", CLIENT,
     "I'm not comfortable keeping this from my sister."),
    ("m06", "2026-02-16T03:02:00+00:00", "sp-a", COUNTERPARTY,
     "If you actually cared about me you would not be making this so difficult. "
     "Prove it to me."),
    ("m07", "2026-02-18T04:41:00+00:00", "sp-a", COUNTERPARTY,
     "My accounts are frozen at the airport and my flight leaves in three hours. "
     "I need you to send 4,000 now or I lose the whole position. There is no time "
     "to think about it."),
    ("m08", "2026-02-18T04:55:00+00:00", "sp-b", CLIENT,
     "I want to stop and check this with someone before I send anything."),
]

# --- synthetic extractor output -------------------------------------------
# Shape matches the strict extractor contract in api_v1/schemas.py.
CANDIDATES = [
    ("PA1", "m01", 0.94, "Declares certainty of a soulmate bond one week into contact.",
     "I have never felt this connected to anyone"),
    ("SE5", "m03", 0.88, "Unverifiable high-status financial narrative introduced before any ask.",
     "I run a private commodities desk in Geneva"),
    ("BD4", "m04", 0.93, "Discourages disclosure to the submitting party's support network.",
     "Please don't tell your friends about us yet"),
    ("GS1", "m06", 0.91, "Conditions care on compliance and demands proof.",
     "If you actually cared about me you would not be making this so difficult"),
    ("FR3", "m07", 0.96, "Emergency transfer request tied to frozen funds and a travel deadline.",
     "I need you to send 4,000 now or I lose the whole position"),
    ("PA2", "m07", 0.90, "Artificial deadline used to foreclose deliberation.",
     "There is no time to think about it"),
]


def build(engine_root: Path) -> dict:
    sys.path.insert(0, str(engine_root))
    cwd = Path.cwd()
    import os

    os.chdir(engine_root)  # the engine resolves Spec/ and VERSION_LOCK.md relatively
    try:
        from engine.render_public_report_v1 import render_public_report_v1
        from engine.render_user_report_v1 import render_legal_report, render_user_report
        from engine.run_case_v1 import run_case_v1

        messages = [
            {
                "message_id": mid,
                "thread_id": THREAD,
                "timestamp": ts,
                "speaker_id": sid,
                "speaker_label": label,
                "text": text,
            }
            for mid, ts, sid, label, text in MESSAGES
        ]
        by_id = {m["message_id"]: m for m in messages}

        instances = []
        for code, mid, confidence, explanation, quote in CANDIDATES:
            body = by_id[mid]["text"]
            start = body.index(quote)
            instances.append(
                {
                    "label_code": code,
                    "message_id": mid,
                    "confidence": confidence,
                    "explanation": explanation,
                    "evidence_spans": [
                        {"start_idx": start, "end_idx": start + len(quote), "quote_text": quote}
                    ],
                }
            )

        case_result = run_case_v1(
            versions=VERSIONS,
            messages=messages,
            extraction_json={"instances": instances},
            now_iso="2026-02-18T09:00:00+00:00",
            provenance={
                "source_filename": "whatsapp-export-2026-02-18.txt",
                "analysis_run_id": "run-9f2c41d8",
                "upload_time": "2026-02-18T08:57:12+00:00",
            },
        )
        return {
            "case_result": case_result,
            "public_report": render_public_report_v1(case_result),
            "user_report": render_user_report(case_result),
            "legal_report": render_legal_report(case_result),
            "transcript": messages,
        }
    finally:
        os.chdir(cwd)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-root", required=True)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "data" / "sample_case.json"))
    args = ap.parse_args()

    bundle = build(Path(args.engine_root).resolve())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False))
    audit = bundle["case_result"].get("audit", {})
    print(f"status={audit.get('status')} tier={bundle['case_result'].get('tier_public')} "
          f"score={bundle['case_result'].get('score_total')} -> {out}")


if __name__ == "__main__":
    main()
