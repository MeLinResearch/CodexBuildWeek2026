import { createFileRoute } from '@tanstack/react-router';

import { StartView } from '@/views/start-view';

export const Route = createFileRoute('/')({
  component: StartView,
});
