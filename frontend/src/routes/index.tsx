import { createFileRoute } from '@tanstack/react-router';

import { loadFixtureData } from '@/api/prefetch';
import { StartView } from '@/views/start-view';

export const Route = createFileRoute('/')({
  loader: ({ context }) => {
    return loadFixtureData(context.queryClient);
  },
  component: StartView,
});
