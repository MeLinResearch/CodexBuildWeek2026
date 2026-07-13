import { useSuspenseQuery } from '@tanstack/react-query';

import { traceabilityMatrixQuery } from '@/api/queries';
import { StatusChip } from '@/components/status-chip';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

const TraceabilityMatrix = () => {
  const { data: matrix } = useSuspenseQuery(traceabilityMatrixQuery);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Traceability Matrix</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Requirement</TableHead>
              <TableHead>Test</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Failures</TableHead>
              <TableHead>Patch</TableHead>
              <TableHead>Approval</TableHead>
              <TableHead>Rerun</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {matrix.map((row) => (
              <TableRow key={row.requirement_id}>
                <TableCell>{row.requirement_id}</TableCell>
                <TableCell>{row.test_id}</TableCell>
                <TableCell>
                  <StatusChip status={row.row_status} />
                </TableCell>
                <TableCell>{row.failure_ids.join(', ')}</TableCell>
                <TableCell>{row.patch_id}</TableCell>
                <TableCell>pending</TableCell>
                <TableCell>not started</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export { TraceabilityMatrix };
