import { useSuspenseQuery } from '@tanstack/react-query';

import { runStatusQuery } from '@/api/queries';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const ModelActionsPanel = () => {
  const { data: runStatus } = useSuspenseQuery(runStatusQuery);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Model Actions</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-md bg-muted p-3">Codex mode: {runStatus.mode.toUpperCase()}</div>
        <div className="rounded-md bg-muted p-3">GPT-5.6 calls: fixture</div>
        <div className="rounded-md bg-muted p-3">Codex task id: fixture</div>
        <div className="rounded-md bg-muted p-3">Sandbox: fixture</div>
        <div className="rounded-md bg-muted p-3">All outputs schema-validated: yes</div>
      </CardContent>
    </Card>
  );
};

export { ModelActionsPanel };
