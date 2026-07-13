import runStatus from '../mocks/run_status.fixture.json';
import matrix from '../mocks/traceability_matrix.fixture.json';
import failure from '../mocks/failed_record_FAIL-001.fixture.json';
import patch from '../mocks/patch_PATCH-001.fixture.json';
import stats from '../mocks/summary_stats.fixture.json';

export const USE_API = false;

async function getJson(path: string, mock: unknown) {
  if (!USE_API) return mock;
  const response = await fetch(path);
  if (!response.ok) throw new Error(`API request failed: ${path}`);
  return response.json();
}

export const api = {
  runStatus: () => getJson('/api/runs/RUN-001', runStatus),
  matrix: () => getJson('/api/runs/RUN-001/matrix', matrix),
  failure: () => getJson('/api/runs/RUN-001/failures/FAIL-001', failure),
  patch: () => getJson('/api/patches/PATCH-001', patch),
  stats: () => stats,
};

export { runStatus, matrix, failure, patch, stats };
