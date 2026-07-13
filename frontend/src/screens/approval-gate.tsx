import { useSuspenseQuery } from '@tanstack/react-query';

import { patchQuery } from '@/api/queries';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const ApprovalGate = () => {
  const { data: patch } = useSuspenseQuery(patchQuery);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Approval Gate</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p>
          {patch.patch_id} affects {patch.failure_ids.join(', ')}
        </p>
        <pre className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs whitespace-pre-wrap">{patch.diff}</pre>
      </CardContent>
    </Card>
  );
};

export { ApprovalGate };
