import { afterEach, describe, expect, test } from 'bun:test';

import { api } from '@/api/client';

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

const jsonResponse = (payload: unknown, init?: ResponseInit): Response => {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
};

describe('api client', () => {
  test('createFixtureRun posts the exact request', async () => {
    globalThis.fetch = ((url: string | URL | Request, init?: RequestInit) => {
      expect(url).toBe('/api/runs');
      expect(init?.method).toBe('POST');
      expect(new Headers(init?.headers).get('Accept')).toBe('application/json');
      expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json');
      expect(JSON.parse(String(init?.body))).toEqual({ mode: 'fixture', fixture_set: 'core-banking' });
      return Promise.resolve(jsonResponse({ run_id: 'RUN-001' }));
    }) as unknown as typeof fetch;

    await expect(api.createFixtureRun()).resolves.toEqual({ run_id: 'RUN-001' });
  });

  test('createLiveRun posts the exact canonical request', async () => {
    globalThis.fetch = ((url: string | URL | Request, init?: RequestInit) => {
      expect(url).toBe('/api/runs');
      expect(init?.method).toBe('POST');
      expect(JSON.parse(String(init?.body))).toEqual({
        mode: 'live',
        implementation_doc_path: 'fixtures/implementation_doc.md',
        source_data_path: 'fixtures/source_data/accounts.csv',
        target_schema_path: 'fixtures/schemas/target_schema.json',
      });
      return Promise.resolve(jsonResponse({ run_id: 'RUN-002' }));
    }) as unknown as typeof fetch;

    await expect(api.createLiveRun()).resolves.toEqual({ run_id: 'RUN-002' });
  });

  test('approvePatch preserves the decision request', async () => {
    globalThis.fetch = ((url: string | URL | Request, init?: RequestInit) => {
      expect(url).toBe('/api/patches/PATCH-001/approve');
      expect(init?.method).toBe('POST');
      const body = JSON.parse(String(init?.body));
      expect(body.actor).toBe('melinda.emerson');
      expect(body.note).toBe('Approved for deterministic rerun');
      return Promise.resolve(jsonResponse({ patch_id: 'PATCH-001', status: 'approved', actor: body.actor, note: body.note }));
    }) as unknown as typeof fetch;

    await api.approvePatch('PATCH-001', 'melinda.emerson', 'Approved for deterministic rerun');
  });

  test('rerun uses the persisted backend endpoint', async () => {
    globalThis.fetch = ((url: string | URL | Request, init?: RequestInit) => {
      expect(url).toBe('/api/runs/RUN-001/rerun');
      expect(init?.method).toBe('POST');
      return Promise.resolve(jsonResponse({ run_id: 'RUN-001', status: 'rerun complete', state: 'EVIDENCE_READY', mode: 'fixture' }));
    }) as unknown as typeof fetch;

    await expect(api.rerun('RUN-001')).resolves.toEqual({ run_id: 'RUN-001', status: 'rerun complete', state: 'EVIDENCE_READY', mode: 'fixture' });
  });

  test('non-2xx responses throw ApiRequestError', async () => {
    globalThis.fetch = (() => {
      return Promise.resolve(jsonResponse({ error: 'conflict' }, { status: 409 }));
    }) as unknown as typeof fetch;

    try {
      await api.rerun('RUN-001');
      throw new Error('expected failure');
    } catch (error) {
      expect((error as Error).name).toBe('ApiRequestError');
      expect((error as { status: number }).status).toBe(409);
      expect((error as { url: string }).url).toBe('/api/runs/RUN-001/rerun');
    }
  });
});
