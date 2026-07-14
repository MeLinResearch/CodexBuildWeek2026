import { Hono } from 'hono';

import failure001Fixture from '@/mocks/failed_record_FAIL-001.fixture.json';
import failure002Fixture from '@/mocks/failed_record_FAIL-002.fixture.json';
import failure003Fixture from '@/mocks/failed_record_FAIL-003.fixture.json';
import patch001Fixture from '@/mocks/patch_PATCH-001.fixture.json';
import runStatus001Fixture from '@/mocks/run_status.fixture.json';
import failure004Fixture from '@/mocks/run-002/failed_record_FAIL-004.fixture.json';
import failure005Fixture from '@/mocks/run-002/failed_record_FAIL-005.fixture.json';
import failure006Fixture from '@/mocks/run-002/failed_record_FAIL-006.fixture.json';
import patch002Fixture from '@/mocks/run-002/patch_PATCH-002.fixture.json';
import runStatus002Fixture from '@/mocks/run-002/run_status.fixture.json';
import matrix002Fixture from '@/mocks/run-002/traceability_matrix.fixture.json';
import failure007Fixture from '@/mocks/run-003/failed_record_FAIL-007.fixture.json';
import failure008Fixture from '@/mocks/run-003/failed_record_FAIL-008.fixture.json';
import failure009Fixture from '@/mocks/run-003/failed_record_FAIL-009.fixture.json';
import patch003Fixture from '@/mocks/run-003/patch_PATCH-003.fixture.json';
import runStatus003Fixture from '@/mocks/run-003/run_status.fixture.json';
import matrix003Fixture from '@/mocks/run-003/traceability_matrix.fixture.json';
import matrix001Fixture from '@/mocks/traceability_matrix.fixture.json';

type TRunDataset = {
  status: typeof runStatus001Fixture;
  matrix: typeof matrix001Fixture;
  failures: (typeof failure001Fixture)[];
  patch: typeof patch001Fixture;
};

/* RUN-001 mirrors the backend fixture API byte for byte. RUN-002 and
 * RUN-003 are the frontend demo sets, served through the same frozen
 * route shapes. */
const RUNS: Record<string, TRunDataset> = {
  'RUN-001': {
    status: runStatus001Fixture,
    matrix: matrix001Fixture,
    failures: [failure001Fixture, failure002Fixture, failure003Fixture],
    patch: patch001Fixture,
  },
  'RUN-002': {
    status: runStatus002Fixture,
    matrix: matrix002Fixture,
    failures: [failure004Fixture, failure005Fixture, failure006Fixture],
    patch: patch002Fixture,
  },
  'RUN-003': {
    status: runStatus003Fixture,
    matrix: matrix003Fixture,
    failures: [failure007Fixture, failure008Fixture, failure009Fixture],
    patch: patch003Fixture,
  },
};

const app = new Hono();

app.get('/api/runs/:runId', (context) => {
  const run = RUNS[context.req.param('runId')];

  if (!run) {
    return context.json({ detail: 'run not found' }, 404);
  }

  return context.json(run.status);
});

app.get('/api/runs/:runId/matrix', (context) => {
  const run = RUNS[context.req.param('runId')];

  if (!run) {
    return context.json({ detail: 'run not found' }, 404);
  }

  return context.json(run.matrix);
});

app.get('/api/runs/:runId/failures/:failureId', (context) => {
  const run = RUNS[context.req.param('runId')];
  const failure = run?.failures.find((candidate) => candidate.failure_id === context.req.param('failureId'));

  if (!run || !failure) {
    return context.json({ detail: 'failure not found' }, 404);
  }

  return context.json(failure);
});

app.get('/api/runs/:runId/patches', (context) => {
  const run = RUNS[context.req.param('runId')];

  if (!run) {
    return context.json({ detail: 'run not found' }, 404);
  }

  return context.json([run.patch]);
});

app.get('/api/patches/:patchId', (context) => {
  const patch = Object.values(RUNS).find((run) => run.patch.patch_id === context.req.param('patchId'))?.patch;

  if (!patch) {
    return context.json({ detail: 'patch not found' }, 404);
  }

  return context.json(patch);
});

app.post('/api/patches/:patchId/approve', async (context) => {
  const patch = Object.values(RUNS).find((run) => run.patch.patch_id === context.req.param('patchId'))?.patch;

  if (!patch) {
    return context.json({ detail: 'patch not found' }, 404);
  }

  const request = await context.req.json<{ actor: string; note?: string | null }>();
  return context.json({ patch_id: patch.patch_id, status: 'approved', actor: request.actor, note: request.note ?? null });
});

app.post('/api/patches/:patchId/reject', async (context) => {
  const patch = Object.values(RUNS).find((run) => run.patch.patch_id === context.req.param('patchId'))?.patch;

  if (!patch) {
    return context.json({ detail: 'patch not found' }, 404);
  }

  const request = await context.req.json<{ actor: string; note?: string | null }>();
  return context.json({ patch_id: patch.patch_id, status: 'rejected', actor: request.actor, note: request.note ?? null });
});

app.post('/api/runs/:runId/rerun', (context) => {
  const run = RUNS[context.req.param('runId')];

  if (!run) {
    return context.json({ detail: 'run not found' }, 404);
  }

  return context.json({ run_id: run.status.run_id, status: 'rerun accepted', mode: 'fixture' });
});

app.get('/api/runs/:runId/evidence', (context) => {
  const run = RUNS[context.req.param('runId')];

  if (!run) {
    return context.json({ detail: 'run not found' }, 404);
  }

  const requirements = run.matrix.map((row) => `<li>${row.requirement_id}</li>`).join('');
  const failures = run.failures.map((failure) => `<li>${failure.failure_id}</li>`).join('');
  const html = `<!doctype html><html><head><title>Release Assurance Evidence Pack</title></head><body><h1>Release Assurance Evidence Pack</h1><p>run_id ${run.status.run_id}</p><p>mode fixture</p><ul>${requirements}</ul><ul>${failures}</ul><p>${run.patch.patch_id}</p><p>Fixture evidence, no live model calls</p></body></html>`;
  return context.html(html);
});

export { app };
