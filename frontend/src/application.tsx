import { Suspense, useRef } from 'react';

import { ModelActionsPanel } from '@/components/model-actions-panel';
import { TopBar } from '@/components/top-bar';
import { Skeleton } from '@/components/ui/skeleton';
import { demoById } from '@/lib/demos';
import { RunUiProvider, useRunUi } from '@/state/run-store';
import { RunTimeline } from '@/views/run-timeline';
import { StartView } from '@/views/start-view';

const TimelineFallback = () => {
  return (
    <div className="mx-auto w-full max-w-[880px] space-y-4">
      <Skeleton className="h-14 w-2/3" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
};

const Workspace = () => {
  const { demoId } = useRunUi();
  const demo = demoId ? demoById(demoId) : undefined;
  const refMain = useRef<HTMLElement>(null);

  return (
    <div className="flex h-svh flex-col">
      <TopBar />
      <div className="relative flex flex-1 overflow-hidden">
        <main ref={refMain} className="flex-1 overflow-y-auto px-6 py-6">
          {demo ? (
            <Suspense fallback={<TimelineFallback />}>
              <RunTimeline key={demo.id} demo={demo} refScroll={refMain} />
            </Suspense>
          ) : (
            <StartView />
          )}
        </main>
      </div>
      <ModelActionsPanel />
    </div>
  );
};

const Application = () => {
  return (
    <RunUiProvider>
      <Workspace />
    </RunUiProvider>
  );
};

export { Application };
