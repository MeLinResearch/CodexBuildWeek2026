import failure from '../mocks/failed_record_FAIL-001.fixture.json';

export function RecordDrilldown() {
  return <section className="screen"><h2>Record Drilldown</h2><p>{failure.failure_id} · {failure.record_id} · {failure.field}</p><p>Expected: {failure.expected}</p><p>Actual: {failure.actual}</p></section>;
}
