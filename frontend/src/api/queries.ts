import { queryOptions } from '@tanstack/react-query';

import { api } from '@/api/client';

const RUN_ID_FIXTURE = 'RUN-001';
const FAILURE_ID_FIXTURE = 'FAIL-001';
const PATCH_ID_FIXTURE = 'PATCH-001';

const runStatusQuery = queryOptions({
  queryKey: ['runs', RUN_ID_FIXTURE, 'status'],
  queryFn: api.runStatus,
});

const traceabilityMatrixQuery = queryOptions({
  queryKey: ['runs', RUN_ID_FIXTURE, 'matrix'],
  queryFn: api.matrix,
});

const failureQuery = queryOptions({
  queryKey: ['runs', RUN_ID_FIXTURE, 'failures', FAILURE_ID_FIXTURE],
  queryFn: api.failure,
});

const patchQuery = queryOptions({
  queryKey: ['patches', PATCH_ID_FIXTURE],
  queryFn: api.patch,
});

const summaryStatsQuery = queryOptions({
  queryKey: ['runs', RUN_ID_FIXTURE, 'summary-stats-fixture'],
  queryFn: api.summaryStats,
});

export { failureQuery, patchQuery, runStatusQuery, summaryStatsQuery, traceabilityMatrixQuery };
