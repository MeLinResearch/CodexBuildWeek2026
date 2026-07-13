import matrix from '../mocks/traceability_matrix.fixture.json';
import { StatusChip } from '../components/StatusChip';

export function TraceabilityMatrix() {
  return <section className="screen"><h1>Traceability Matrix</h1><table><thead><tr><th>Requirement</th><th>Test</th><th>Status</th><th>Failures</th><th>Patch</th><th>Approval</th><th>Rerun</th></tr></thead><tbody>{matrix.map((row) => <tr key={row.requirement_id}><td>{row.requirement_id}</td><td>{row.test_id}</td><td><StatusChip status={row.row_status} /></td><td>{row.failure_ids.join(', ')}</td><td>{row.patch_id}</td><td>pending</td><td>not started</td></tr>)}</tbody></table></section>;
}
