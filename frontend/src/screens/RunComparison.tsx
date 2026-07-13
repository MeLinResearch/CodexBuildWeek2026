import stats from '../mocks/summary_stats.fixture.json';

export function RunComparison() {
  return <section className="screen"><h2>Run Comparison</h2><p>Run {stats.run_id}: {stats.requirements} requirements, {stats.tests} tests, {stats.failures} failures, {stats.patches} patch set.</p></section>;
}
