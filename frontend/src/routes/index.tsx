import type { QueryClient } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';

import { failureQuery, patchesQuery, runStatusQuery, traceabilityMatrixQuery } from '@/api/queries';
import { Application } from '@/application';
import { DEMOS } from '@/lib/demos';

/* Everything the timeline renders is prefetched here so no step
 * suspends (and flickers the page) mid-story. */
const loadRun = async (queryClient: QueryClient, runId: string): Promise<void> => {
  const [matrix] = await Promise.all([
    queryClient.ensureQueryData(traceabilityMatrixQuery(runId)),
    queryClient.ensureQueryData(runStatusQuery(runId)),
    queryClient.ensureQueryData(patchesQuery(runId)),
  ]);

  await Promise.all(matrix.flatMap((row) => row.failure_ids).map((failureId) => queryClient.ensureQueryData(failureQuery(runId, failureId))));
};

const loadFixtureData = async (queryClient: QueryClient): Promise<void> => {
  await Promise.all(DEMOS.map((demo) => loadRun(queryClient, demo.runId)));
};

export const Route = createFileRoute('/')({
  loader: ({ context }) => {
    return loadFixtureData(context.queryClient);
  },
  component: Application,
});
