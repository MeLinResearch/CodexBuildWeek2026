from __future__ import annotations

from html import escape
from typing import Any

from app.store.models import FailureRow, PatchRow, RequirementRow, RunRow, StateTransitionRow, TestRow


def _text(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, list):
        return ", ".join(_text(item) for item in value) if value else "none"
    return escape(str(value))


def _field(label: str, value: Any) -> str:
    return f"<dt>{escape(label)}</dt><dd>{_text(value)}</dd>"


def _decision(patch: PatchRow) -> str:
    actor = _text(patch.approved_by)
    decided = _text(patch.approved_at)
    if patch.status == "pending":
        return "Awaiting human decision. The proposed patch has not been applied and no rerun has occurred."
    if patch.status == "approved":
        return f"The patch was approved. Decision actor: {actor}. Decision time: {decided}. Patch application has not yet been recorded."
    if patch.status == "rejected":
        return f"The patch was rejected. Decision actor: {actor}. Decision time: {decided}. No rerun was performed."
    if patch.status == "applied":
        return f"The patch was approved and applied. Decision actor: {actor}. Decision time: {decided}. Applied at: {_text(patch.applied_at)}."
    return f"Patch application failed. Decision actor: {actor}. Decision time: {decided}."


def render_evidence_html(
    *,
    run: RunRow,
    requirements: list[RequirementRow],
    tests: list[TestRow],
    failures: list[FailureRow],
    patch: PatchRow,
    matrix: list[dict],
    transitions: list[StateTransitionRow],
) -> str:
    provenance = requirements[0].provenance
    summary = {
        "requirements": len(requirements),
        "tests": len(tests),
        "failures": len(failures),
        "blocking failures": sum(1 for failure in failures if failure.severity == "blocking"),
        "patches": 1,
    }
    matrix_rows = "".join(
        "<tr>"
        f"<td>{_text(row.get('requirement_id'))}</td>"
        f"<td>{_text(row.get('test_id'))}</td>"
        f"<td>{_text(row.get('row_status'))}</td>"
        f"<td>{_text(row.get('failure_ids'))}</td>"
        f"<td>{_text(row.get('patch_id'))}</td>"
        f"<td>{_text(row.get('evidence_refs'))}</td>"
        "</tr>"
        for row in matrix
    )
    failure_blocks = "".join(
        "<section class=\"item\"><dl>"
        f"{_field('failure_id', failure.failure_id)}"
        f"{_field('requirement_id', failure.requirement_id)}"
        f"{_field('severity', failure.severity)}"
        f"{_field('record_id', failure.record_id)}"
        f"{_field('field', failure.field)}"
        f"{_field('expected', failure.expected)}"
        f"{_field('actual', failure.actual)}"
        f"{_field('record_hash', failure.record_hash)}"
        f"{_field('provenance.validation_status', failure.provenance.get('validation_status'))}"
        "</dl></section>"
        for failure in failures
    )
    transition_rows = "".join(
        "<tr>"
        f"<td>{_text(transition.from_state)}</td>"
        f"<td>{_text(transition.to_state)}</td>"
        f"<td>{_text(transition.actor)}</td>"
        f"<td>{_text(transition.at)}</td>"
        "</tr>"
        for transition in transitions
    )
    requirement_text = "".join(f"<li>{_text(requirement.requirement_id)}: {_text(requirement.text)}</li>" for requirement in requirements)
    summary_fields = "".join(_field(key, value) for key, value in summary.items())
    evidence_notice = (
        "Fixture evidence, no live model calls"
        if run.mode == "fixture"
        else "Live evidence generated from validated GPT and Codex outputs"
    )
    return f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Release Assurance Evidence Pack</title>
<style>
body {{ font-family: Inter, Arial, sans-serif; color: #172033; margin: 32px; line-height: 1.45; }}
h1, h2 {{ color: #0f172a; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; }}
th, td {{ border: 1px solid #cbd5e1; padding: 8px; text-align: left; vertical-align: top; }}
dl {{ display: grid; grid-template-columns: 220px 1fr; gap: 6px 14px; }}
dt {{ font-weight: 700; }}
dd {{ margin: 0; }}
pre {{ white-space: pre-wrap; border: 1px solid #cbd5e1; background: #f8fafc; padding: 12px; }}
.item {{ break-inside: avoid; border: 1px solid #e2e8f0; padding: 12px; margin: 10px 0; }}
footer {{ margin-top: 32px; font-size: 12px; color: #475569; }}
</style>
</head>
<body>
<h1>Release Assurance Evidence Pack</h1>
<p>{evidence_notice}</p>
<dl>{_field('run_id', run.run_id)}{_field('mode', run.mode)}{_field('state', run.state)}{_field('created_at', run.created_at)}{_field('updated_at', run.updated_at)}{_field('schema_version', run.schema_version)}</dl>
<h2>Run provenance</h2>
<dl>{_field('producer', provenance.get('producer'))}{_field('client', provenance.get('client'))}{_field('mode', provenance.get('mode'))}{_field('validation_status', provenance.get('validation_status'))}{_field('schema_version', provenance.get('schema_version'))}{_field('source_artifact_ids', provenance.get('source_artifact_ids'))}{_field('created_at', provenance.get('created_at'))}</dl>
<h2>Summary</h2>
<dl>{summary_fields}</dl>
<ul>{requirement_text}</ul>
<h2>Traceability matrix</h2>
<table><thead><tr><th>Requirement</th><th>Test</th><th>Status</th><th>Failures</th><th>Patch</th><th>Evidence refs</th></tr></thead><tbody>{matrix_rows}</tbody></table>
<h2>Failure evidence</h2>
{failure_blocks}
<h2>Proposed patch</h2>
<dl>{_field('patch_id', patch.patch_id)}{_field('status', patch.status)}{_field('failure_ids', patch.failure_ids)}{_field('provenance.client', patch.provenance.get('client'))}</dl>
<pre>{_text(patch.diff)}</pre>
<h2>Decision record</h2>
<p>{_decision(patch)}</p>
<h2>State transition audit trail</h2>
<table><thead><tr><th>From</th><th>To</th><th>Actor</th><th>At</th></tr></thead><tbody>{transition_rows}</tbody></table>
<footer>This document was generated from schema-validated contract objects.</footer>
</body>
</html>'''
