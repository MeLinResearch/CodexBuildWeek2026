import type failureFixture from '@/mocks/failed_record_FAIL-001.fixture.json';
import type patchFixture from '@/mocks/patch_PATCH-001.fixture.json';
import type runStatusFixture from '@/mocks/run_status.fixture.json';
import summaryStatsFixture from '@/mocks/summary_stats.fixture.json';
import type traceabilityMatrixFixture from '@/mocks/traceability_matrix.fixture.json';

type TFailure = typeof failureFixture;
type TPatch = typeof patchFixture;
type TRunStatus = typeof runStatusFixture;
type TSummaryStats = typeof summaryStatsFixture;
type TTraceabilityMatrix = typeof traceabilityMatrixFixture;

type TApiRequestError = Error & {
  status: number;
  url: string;
};

const createApiRequestError = (url: string, status: number): TApiRequestError => {
  const error = new Error(`API request failed with status ${status}: ${url}`);
  return Object.assign(error, {
    name: 'ApiRequestError',
    status,
    url,
  });
};

const getJson = async <TResponse>(url: string): Promise<TResponse> => {
  const response = await fetch(url, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw createApiRequestError(url, response.status);
  }

  const payload: unknown = await response.json();
  return payload as TResponse;
};

const api = {
  runStatus: (): Promise<TRunStatus> => {
    return getJson<TRunStatus>('/api/runs/RUN-001');
  },
  matrix: (): Promise<TTraceabilityMatrix> => {
    return getJson<TTraceabilityMatrix>('/api/runs/RUN-001/matrix');
  },
  failure: (): Promise<TFailure> => {
    return getJson<TFailure>('/api/runs/RUN-001/failures/FAIL-001');
  },
  patch: (): Promise<TPatch> => {
    return getJson<TPatch>('/api/patches/PATCH-001');
  },
  summaryStats: (): Promise<TSummaryStats> => {
    return Promise.resolve(summaryStatsFixture);
  },
};

export { api };
