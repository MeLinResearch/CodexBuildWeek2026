import { useSuspenseQuery } from '@tanstack/react-query';

import { failureQuery } from '@/api/queries';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const RecordDrilldown = () => {
  const { data: failure } = useSuspenseQuery(failureQuery);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Record Drilldown</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <p>
          {failure.failure_id} · {failure.record_id} · {failure.field}
        </p>
        <p>Expected: {failure.expected}</p>
        <p>Actual: {failure.actual}</p>
      </CardContent>
    </Card>
  );
};

export { RecordDrilldown };
