import { useSuspenseQuery } from '@tanstack/react-query';

import { summaryStatsQuery } from '@/api/queries';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const RunComparison = () => {
  const { data: stats } = useSuspenseQuery(summaryStatsQuery);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Run Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <p>
          Run {stats.run_id}: {stats.requirements} requirements, {stats.tests} tests, {stats.failures} failures, {stats.patches} patch set.
        </p>
      </CardContent>
    </Card>
  );
};

export { RunComparison };
