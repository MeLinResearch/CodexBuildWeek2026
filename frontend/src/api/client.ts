import type failureFixture from '@/mocks/failed_record_FAIL-001.fixture.json';
import type patchFixture from '@/mocks/patch_PATCH-001.fixture.json';
import type runStatusFixture from '@/mocks/run_status.fixture.json';
import type traceabilityMatrixFixture from '@/mocks/traceability_matrix.fixture.json';

type TFailure = typeof failureFixture;
type TPatch = typeof patchFixture;
type TRunStatus = Omit<typeof runStatusFixture, 'mode'> & { mode: 'fixture' | 'live' };
type TTraceabilityRowStatus = 'pending' | 'passed' | 'failed' | 'patch_pending' | 'patch_approved' | 'rerun_passed';
type TTraceabilityMatrixRow = Omit<(typeof traceabilityMatrixFixture)[number], 'row_status'> & {
  row_status: TTraceabilityRowStatus;
};
type TTraceabilityMatrix = TTraceabilityMatrixRow[];

interface ICreateRunResult {
  run_id: string;
}

interface IApprovalResult {
  patch_id: string;
  status: 'approved' | 'rejected';
  actor: string;
  note: string | null;
}

interface IRerunResult {
  run_id: string;
  status: string;
  state: 'EVIDENCE_READY';
  mode: 'fixture' | 'live';
}

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

const requestJson = async <TResponse>(url: string, init?: RequestInit): Promise<TResponse> => {
  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw createApiRequestError(url, response.status);
  }

  const payload: unknown = await response.json();
  return payload as TResponse;
};

const api = {
  createFixtureRun: (): Promise<ICreateRunResult> => {
    return requestJson<ICreateRunResult>('/api/runs', {
      method: 'POST',
      body: JSON.stringify({ mode: 'fixture', fixture_set: 'core-banking' }),
    });
  },
  createLiveRun: (): Promise<ICreateRunResult> => {
    return requestJson<ICreateRunResult>('/api/runs', {
      method: 'POST',
      body: JSON.stringify({
        mode: 'live',
        implementation_doc_path: 'fixtures/implementation_doc.md',
        source_data_path: 'fixtures/source_data/accounts.csv',
        target_schema_path: 'fixtures/schemas/target_schema.json',
      }),
    });
  },
  runStatus: (runId: string): Promise<TRunStatus> => {
    return requestJson<TRunStatus>(`/api/runs/${runId}`);
  },
  matrix: (runId: string): Promise<TTraceabilityMatrix> => {
    return requestJson<TTraceabilityMatrix>(`/api/runs/${runId}/matrix`);
  },
  failure: (runId: string, failureId: string): Promise<TFailure> => {
    return requestJson<TFailure>(`/api/runs/${runId}/failures/${failureId}`);
  },
  patches: (runId: string): Promise<TPatch[]> => {
    return requestJson<TPatch[]>(`/api/runs/${runId}/patches`);
  },
  approvePatch: (patchId: string, actor: string, note: string | null): Promise<IApprovalResult> => {
    return requestJson<IApprovalResult>(`/api/patches/${patchId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ actor, note }),
    });
  },
  rejectPatch: (patchId: string, actor: string, note: string | null): Promise<IApprovalResult> => {
    return requestJson<IApprovalResult>(`/api/patches/${patchId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ actor, note }),
    });
  },
  rerun: (runId: string): Promise<IRerunResult> => {
    return requestJson<IRerunResult>(`/api/runs/${runId}/rerun`, { method: 'POST' });
  },
};

export type { TFailure, TPatch };
export { api };
