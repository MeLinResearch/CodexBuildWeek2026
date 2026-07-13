import { Hono } from 'hono';

import failureFixture from '@/mocks/failed_record_FAIL-001.fixture.json';
import patchFixture from '@/mocks/patch_PATCH-001.fixture.json';
import runStatusFixture from '@/mocks/run_status.fixture.json';
import traceabilityMatrixFixture from '@/mocks/traceability_matrix.fixture.json';

const app = new Hono();

app.get('/api/runs/:runId', (context) => {
  if (context.req.param('runId') !== runStatusFixture.run_id) {
    return context.json({ detail: 'run not found' }, 404);
  }

  return context.json(runStatusFixture);
});

app.get('/api/runs/:runId/matrix', (context) => {
  if (context.req.param('runId') !== runStatusFixture.run_id) {
    return context.json({ detail: 'run not found' }, 404);
  }

  return context.json(traceabilityMatrixFixture);
});

app.get('/api/runs/:runId/failures/:failureId', (context) => {
  if (context.req.param('runId') !== runStatusFixture.run_id || context.req.param('failureId') !== failureFixture.failure_id) {
    return context.json({ detail: 'failure not found' }, 404);
  }

  return context.json(failureFixture);
});

app.get('/api/patches/:patchId', (context) => {
  if (context.req.param('patchId') !== patchFixture.patch_id) {
    return context.json({ detail: 'patch not found' }, 404);
  }

  return context.json(patchFixture);
});

export { app };
