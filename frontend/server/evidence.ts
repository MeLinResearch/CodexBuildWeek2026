/* The audit-ready evidence pack template, shared by agreement with
 * the backend: the FastAPI generator renders this same structure, so
 * the pack looks identical whichever server produced it. Everything
 * here is a pure function of the run's contract objects; timestamps
 * come from the data, never from the clock, so output stays
 * byte-identical run over run. */

interface IProvenance {
  client: string;
  created_at: string;
  mode: string;
  producer: string;
  run_id: string;
  schema_version: string;
  source_artifact_ids: string[];
  validation_status: string;
}

interface IEvidenceRun {
  status: {
    run_id: string;
    mode: string;
    state: string;
    created_at: string;
    updated_at: string;
    schema_version: string;
    provenance: IProvenance;
  };
  matrix: {
    requirement_id: string;
    test_id: string;
    row_status: string;
    failure_ids: string[];
    patch_id: string;
    evidence_refs: string[];
  }[];
  failures: {
    failure_id: string;
    requirement_id: string;
    record_id: string;
    record_hash: string;
    field: string;
    expected: string;
    actual: string;
    severity: string;
    provenance: IProvenance;
  }[];
  patch: {
    patch_id: string;
    status: string;
    failure_ids: string[];
    diff: string;
    provenance: IProvenance;
  };
}

const escapeHtml = (value: string): string => {
  return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
};

const STYLES = `
  body { margin: 40px auto; max-width: 820px; padding: 0 24px; color: #111;
         font: 14px/1.55 -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
  h1 { font-size: 22px; margin-bottom: 2px; }
  h2 { font-size: 15px; margin: 32px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  th, td { border: 1px solid #ddd; padding: 6px 9px; text-align: left; vertical-align: top; font-size: 13px; }
  th { background: #f5f5f5; font-weight: 600; }
  code, pre { font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; font-size: 12px; }
  pre { background: #f7f7f7; border: 1px solid #ddd; padding: 12px; overflow-x: auto; white-space: pre-wrap; }
  .meta { color: #555; font-size: 13px; }
  .badge { display: inline-block; border: 1px solid #999; border-radius: 3px; padding: 0 6px;
           font-family: ui-monospace, Menlo, monospace; font-size: 11px; text-transform: uppercase; }
  .footer { margin-top: 36px; padding-top: 10px; border-top: 1px solid #ddd; color: #777; font-size: 12px; }
  @media print { body { margin: 0; max-width: none; } }
`;

const renderProvenance = (provenance: IProvenance): string => {
  return `<table>
    <tr><th>Producer</th><td><code>${escapeHtml(provenance.producer)}</code></td>
        <th>Client</th><td><code>${escapeHtml(provenance.client)}</code></td></tr>
    <tr><th>Mode</th><td><code>${escapeHtml(provenance.mode)}</code></td>
        <th>Validation</th><td><code>${escapeHtml(provenance.validation_status)}</code></td></tr>
    <tr><th>Schema version</th><td><code>${escapeHtml(provenance.schema_version)}</code></td>
        <th>Source artifacts</th><td><code>${provenance.source_artifact_ids.map(escapeHtml).join(', ')}</code></td></tr>
    <tr><th>Created</th><td colspan="3"><code>${escapeHtml(provenance.created_at)}</code></td></tr>
  </table>`;
};

const renderMatrix = (matrix: IEvidenceRun['matrix']): string => {
  const rows = matrix
    .map((row) => {
      return `<tr>
        <td><code>${escapeHtml(row.requirement_id)}</code></td>
        <td><code>${escapeHtml(row.test_id)}</code></td>
        <td><code>${escapeHtml(row.row_status)}</code></td>
        <td><code>${row.failure_ids.map(escapeHtml).join(', ') || 'none'}</code></td>
        <td><code>${escapeHtml(row.patch_id)}</code></td>
        <td><code>${row.evidence_refs.map(escapeHtml).join(', ')}</code></td>
      </tr>`;
    })
    .join('');

  return `<table>
    <tr><th>Requirement</th><th>Test</th><th>Status</th><th>Failures</th><th>Patch</th><th>Evidence refs</th></tr>
    ${rows}
  </table>`;
};

const renderFailures = (failures: IEvidenceRun['failures']): string => {
  return failures
    .map((failure) => {
      return `<h3><code>${escapeHtml(failure.failure_id)}</code> <span class="meta">(${escapeHtml(failure.requirement_id)}, severity ${escapeHtml(failure.severity)})</span></h3>
      <table>
        <tr><th>Record</th><td><code>${escapeHtml(failure.record_id)}</code></td>
            <th>Field</th><td><code>${escapeHtml(failure.field)}</code></td></tr>
        <tr><th>Expected</th><td><code>${escapeHtml(failure.expected)}</code></td>
            <th>Actual</th><td><code>${escapeHtml(failure.actual)}</code></td></tr>
        <tr><th>Record hash</th><td><code>${escapeHtml(failure.record_hash)}</code></td>
            <th>Validation</th><td><code>${escapeHtml(failure.provenance.validation_status)}</code></td></tr>
      </table>`;
    })
    .join('');
};

/* The decision section reflects recorded pipeline state only. The
 * stateless fixture server always reports the pre-decision state;
 * the live backend fills in actor, note, and timestamp once a
 * decision is persisted. */
const renderDecision = (state: string): string => {
  if (state === 'PATCH_PENDING') {
    return '<p>Awaiting human decision. The proposed patch has not been applied and no rerun has occurred.</p>';
  }

  return `<p>Run state: <code>${escapeHtml(state)}</code>.</p>`;
};

const renderEvidenceHtml = (run: IEvidenceRun): string => {
  const failureCount = run.failures.length;
  const blockingCount = run.failures.filter((failure) => failure.severity === 'blocking').length;

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Evidence Pack ${escapeHtml(run.status.run_id)}</title>
<style>${STYLES}</style>
</head>
<body>
<h1>Release Assurance Evidence Pack</h1>
<p class="meta">
  <code>${escapeHtml(run.status.run_id)}</code>
  <span class="badge">${escapeHtml(run.status.mode)}</span>
  state <code>${escapeHtml(run.status.state)}</code>,
  created <code>${escapeHtml(run.status.created_at)}</code>,
  updated <code>${escapeHtml(run.status.updated_at)}</code>,
  schema <code>${escapeHtml(run.status.schema_version)}</code>
</p>

<h2>Run provenance</h2>
${renderProvenance(run.status.provenance)}

<h2>Summary</h2>
<table>
  <tr><th>Requirements</th><th>Tests</th><th>Failures</th><th>Blocking</th><th>Patches</th></tr>
  <tr><td>${run.matrix.length}</td><td>${run.matrix.length}</td><td>${failureCount}</td><td>${blockingCount}</td><td>1</td></tr>
</table>

<h2>Traceability matrix</h2>
${renderMatrix(run.matrix)}

<h2>Failure evidence</h2>
${renderFailures(run.failures)}

<h2>Proposed patch</h2>
<p class="meta">
  <code>${escapeHtml(run.patch.patch_id)}</code>
  status <code>${escapeHtml(run.patch.status)}</code>,
  fixes <code>${run.patch.failure_ids.map(escapeHtml).join(', ')}</code>,
  proposed via <code>${escapeHtml(run.patch.provenance.client)}</code>
</p>
<pre>${escapeHtml(run.patch.diff)}</pre>

<h2>Decision record</h2>
${renderDecision(run.status.state)}

<p class="footer">
  Generated from schema-validated contract objects (schema ${escapeHtml(run.status.schema_version)}).
  ${run.status.mode === 'fixture' ? 'Fixture evidence: deterministic replay, 0 live model calls.' : 'Live run evidence.'}
</p>
</body>
</html>`;
};

export { renderEvidenceHtml };
