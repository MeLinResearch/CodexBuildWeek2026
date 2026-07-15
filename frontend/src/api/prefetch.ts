import type { QueryClient } from '@tanstack/react-query';

import { failureQuery, patchesQuery, runStatusQuery, traceabilityMatrixQuery } from '@/api/queries';

/* Everything the timeline renders is prefetched before render so no step suspends mid-story. */
const loadRun = async (queryClient: QueryClient, runId: string): Promise<void> => {
  const [matrix] = await Promise.all([
    queryClient.ensureQueryData(traceabilityMatrixQuery(runId)),
    queryClient.ensureQueryData(runStatusQuery(runId)),
    queryClient.ensureQueryData(patchesQuery(runId)),
  ]);

  await Promise.all(matrix.flatMap((row) => row.failure_ids).map((failureId) => queryClient.ensureQueryData(failureQuery(runId, failureId))));
};

export { loadRun };
