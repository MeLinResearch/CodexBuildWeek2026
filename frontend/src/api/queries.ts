import { queryOptions } from '@tanstack/react-query';

import { api } from '@/api/client';

/* Backend state changes are discrete, so the status query polls
 * instead of streaming. Polling pauses when the run waits on a human
 * (PATCH_PENDING) or is terminal; the approve/reject mutations
 * invalidate the query, and the first refetch resumes the interval
 * if the backend moved the run to an active state. Fixture runs are
 * EVIDENCE_READY after approval plus rerun. */
const IDLE_STATES = new Set(['PATCH_PENDING', 'PATCH_REJECTED', 'EVIDENCE_READY', 'DONE', 'FAILED']);
const POLL_INTERVAL_MS = 1000;

const runStatusQuery = (runId: string) => {
  return queryOptions({
    queryKey: ['runs', runId, 'status'],
    queryFn: () => api.runStatus(runId),
    refetchInterval: (query) => {
      const state = query.state.data?.state;

      if (state && IDLE_STATES.has(state)) {
        return false;
      }

      return POLL_INTERVAL_MS;
    },
  });
};

const traceabilityMatrixQuery = (runId: string) => {
  return queryOptions({
    queryKey: ['runs', runId, 'matrix'],
    queryFn: () => api.matrix(runId),
  });
};

const failureQuery = (runId: string, failureId: string) => {
  return queryOptions({
    queryKey: ['runs', runId, 'failures', failureId],
    queryFn: () => api.failure(runId, failureId),
  });
};

const patchesQuery = (runId: string) => {
  return queryOptions({
    queryKey: ['runs', runId, 'patches'],
    queryFn: () => api.patches(runId),
  });
};

export { failureQuery, patchesQuery, runStatusQuery, traceabilityMatrixQuery };
