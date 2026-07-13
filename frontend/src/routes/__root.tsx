import type { QueryClient } from '@tanstack/react-query';
import { createRootRouteWithContext, Outlet } from '@tanstack/react-router';

import { AppError } from '@/components/app-error';
import { AppPending } from '@/components/app-pending';

interface IRouterContext {
  queryClient: QueryClient;
}

const RootLayout = () => {
  return (
    <div className="isolate min-h-svh">
      <Outlet />
    </div>
  );
};

export const Route = createRootRouteWithContext<IRouterContext>()({
  component: RootLayout,
  errorComponent: AppError,
  pendingComponent: AppPending,
});
