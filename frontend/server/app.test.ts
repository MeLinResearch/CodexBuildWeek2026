import { describe, expect, it } from 'bun:test';
import { app } from '@server/app';
import failureFixture from '@/mocks/failed_record_FAIL-001.fixture.json';
import patchFixture from '@/mocks/patch_PATCH-001.fixture.json';
import runStatusFixture from '@/mocks/run_status.fixture.json';
import failure006Fixture from '@/mocks/run-002/failed_record_FAIL-006.fixture.json';
import patch002Fixture from '@/mocks/run-002/patch_PATCH-002.fixture.json';
import runStatus003Fixture from '@/mocks/run-003/run_status.fixture.json';
import matrix003Fixture from '@/mocks/run-003/traceability_matrix.fixture.json';
import traceabilityMatrixFixture from '@/mocks/traceability_matrix.fixture.json';

describe('Hono fixture API', () => {
  it('serves the backend-parity run fixture', async () => {
    const response = await app.request('/api/runs/RUN-001');

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(runStatusFixture);
  });

  it('serves the backend-parity matrix fixture', async () => {
    const response = await app.request('/api/runs/RUN-001/matrix');

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(traceabilityMatrixFixture);
  });

  it('serves the backend-parity failure fixture', async () => {
    const response = await app.request('/api/runs/RUN-001/failures/FAIL-001');

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(failureFixture);
  });

  it('serves the backend-parity patch fixture', async () => {
    const response = await app.request('/api/patches/PATCH-001');

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(patchFixture);
  });

  it('serves the authored demo runs through the same route shapes', async () => {
    const [status, matrix, failure, patch] = await Promise.all([
      app.request('/api/runs/RUN-003'),
      app.request('/api/runs/RUN-003/matrix'),
      app.request('/api/runs/RUN-002/failures/FAIL-006'),
      app.request('/api/patches/PATCH-002'),
    ]);

    expect(await status.json()).toEqual(runStatus003Fixture);
    expect(await matrix.json()).toEqual(matrix003Fixture);
    expect(await failure.json()).toEqual(failure006Fixture);
    expect(await patch.json()).toEqual(patch002Fixture);
  });

  it('does not serve failures across runs', async () => {
    const response = await app.request('/api/runs/RUN-001/failures/FAIL-004');

    expect(response.status).toBe(404);
  });

  it('returns 404 for unknown fixture identifiers', async () => {
    const responses = await Promise.all([
      app.request('/api/runs/RUN-999'),
      app.request('/api/runs/RUN-001/failures/FAIL-999'),
      app.request('/api/patches/PATCH-999'),
    ]);

    expect(responses.map((response) => response.status)).toEqual([404, 404, 404]);
  });

  it('does not invent a summary API route', async () => {
    const response = await app.request('/api/runs/RUN-001/summary');

    expect(response.status).toBe(404);
  });

  it('lists run patches for the approval gate', async () => {
    const response = await app.request('/api/runs/RUN-002/patches');

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual([patch002Fixture]);
  });

  it('echoes approval decisions like the backend fixture API', async () => {
    const response = await app.request('/api/patches/PATCH-003/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor: 'demo_user', note: 'looks right' }),
    });

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ patch_id: 'PATCH-003', status: 'approved', actor: 'demo_user', note: 'looks right' });
  });

  it('rejects approvals for unknown patches', async () => {
    const response = await app.request('/api/patches/PATCH-999/reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor: 'demo_user', note: 'nope' }),
    });

    expect(response.status).toBe(404);
  });

  it('accepts a rerun request per run', async () => {
    const response = await app.request('/api/runs/RUN-002/rerun', { method: 'POST' });

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ run_id: 'RUN-002', status: 'rerun accepted', mode: 'fixture' });
  });

  it('serves an audit-ready evidence pack per run', async () => {
    const response = await app.request('/api/runs/RUN-003/evidence');

    expect(response.status).toBe(200);
    const html = await response.text();
    expect(html).toContain('RUN-003');
    expect(html).toContain('Run provenance');
    expect(html).toContain('Traceability matrix');
    expect(html).toContain('Failure evidence');
    expect(html).toContain('FAIL-007');
    expect(html).toContain('PATCH-003');
    expect(html).toContain('Decision record');
    expect(html).toContain('Awaiting human decision');
  });

  it('renders the evidence pack deterministically', async () => {
    const first = await (await app.request('/api/runs/RUN-001/evidence')).text();
    const second = await (await app.request('/api/runs/RUN-001/evidence')).text();

    expect(first).toBe(second);
  });
});
