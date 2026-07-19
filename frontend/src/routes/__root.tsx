import type { QueryClient } from '@tanstack/react-query';
import { createRootRouteWithContext, Outlet } from '@tanstack/react-router';

import { AppError } from '@/components/app-error';
import { AppPending } from '@/components/app-pending';
import { DemoDirectorOverlayView } from '@/components/director/overlay';
import { TopBar } from '@/components/top-bar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { refAppViewport } from '@/lib/app-viewport';

interface IRouterContext {
  queryClient: QueryClient;
}

/* The app shell: one ScrollArea owns all scrolling (no browser
 * scrollbar) and the top bar sticks inside it so content slides
 * under the blur. */
const RootLayout = () => {
  return (
    <>
      <div className="isolate relative flex h-svh flex-col faded-bottom">
        <div className="app-aurora" aria-hidden="true" />
        <ScrollArea className="min-h-0 flex-1" viewportClassName="h-full" refViewport={refAppViewport}>
          <TopBar />
          <main className="px-6 pt-4 pb-6">
            <Outlet />
          </main>
        </ScrollArea>
      </div>
      <DemoDirectorOverlayView />
    </>
  );
};

export const Route = createRootRouteWithContext<IRouterContext>()({
  component: RootLayout,
  errorComponent: AppError,
  pendingComponent: AppPending,
});
