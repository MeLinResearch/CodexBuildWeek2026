import { createFileRoute, redirect } from '@tanstack/react-router';
import { Suspense } from 'react';

import { loadRun } from '@/api/prefetch';
import { Skeleton } from '@/components/ui/skeleton';
import { refAppViewport } from '@/lib/app-viewport';
import { demoByRunId } from '@/lib/demos';
import { RunTimeline } from '@/views/run-timeline';

const TimelineFallback = () => {
  return (
    <div className="mx-auto w-full max-w-[880px] space-y-4">
      <Skeleton className="h-14 w-2/3" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
};

const RunView = () => {
  const { runId } = Route.useParams();
  const demo = demoByRunId(runId);

  if (!demo) {
    return null;
  }

  return (
    <Suspense fallback={<TimelineFallback />}>
      <RunTimeline key={demo.id} demo={demo} refScroll={refAppViewport} />
    </Suspense>
  );
};

export const Route = createFileRoute('/$runId')({
  loader: ({ context, params }) => {
    const demo = demoByRunId(params.runId);

    if (!demo) {
      throw redirect({ to: '/' });
    }

    return loadRun(context.queryClient, demo.runId);
  },
  component: RunView,
});
