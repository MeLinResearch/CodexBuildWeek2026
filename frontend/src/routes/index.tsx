import type { QueryClient } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';

import { failureQuery, patchQuery, runStatusQuery, summaryStatsQuery, traceabilityMatrixQuery } from '@/api/queries';
import { Application } from '@/application';

const loadFixtureData = async (queryClient: QueryClient): Promise<void> => {
  await Promise.all([
    queryClient.ensureQueryData(runStatusQuery),
    queryClient.ensureQueryData(traceabilityMatrixQuery),
    queryClient.ensureQueryData(failureQuery),
    queryClient.ensureQueryData(patchQuery),
    queryClient.ensureQueryData(summaryStatsQuery),
  ]);
};

export const Route = createFileRoute('/')({
  loader: ({ context }) => {
    return loadFixtureData(context.queryClient);
  },
  component: Application,
});
