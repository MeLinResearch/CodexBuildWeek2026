import { queryOptions } from '@tanstack/react-query';

import { api } from '@/api/client';

const runStatusQuery = (runId: string) => {
  return queryOptions({
    queryKey: ['runs', runId, 'status'],
    queryFn: () => api.runStatus(runId),
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
