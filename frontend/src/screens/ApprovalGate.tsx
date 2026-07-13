import patch from '../mocks/patch_PATCH-001.fixture.json';

export function ApprovalGate() {
  return <section className="screen"><h2>Approval Gate</h2><p>{patch.patch_id} affects {patch.failure_ids.join(', ')}</p><pre>{patch.diff}</pre></section>;
}
