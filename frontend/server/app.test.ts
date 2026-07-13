import { describe, expect, it } from 'bun:test';
import { app } from '@server/app';
import failureFixture from '@/mocks/failed_record_FAIL-001.fixture.json';
import patchFixture from '@/mocks/patch_PATCH-001.fixture.json';
import runStatusFixture from '@/mocks/run_status.fixture.json';
import traceabilityMatrixFixture from '@/mocks/traceability_matrix.fixture.json';

describe('Hono fixture API', () => {
  it('serves the existing run fixture', async () => {
    const response = await app.request('/api/runs/RUN-001');

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(runStatusFixture);
  });

  it('serves the existing matrix fixture', async () => {
    const response = await app.request('/api/runs/RUN-001/matrix');

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(traceabilityMatrixFixture);
  });

  it('serves the existing failure fixture', async () => {
    const response = await app.request('/api/runs/RUN-001/failures/FAIL-001');

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(failureFixture);
  });

  it('serves the existing patch fixture', async () => {
    const response = await app.request('/api/patches/PATCH-001');

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(patchFixture);
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
});
