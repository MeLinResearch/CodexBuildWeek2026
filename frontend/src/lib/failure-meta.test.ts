import { describe, expect, test } from 'bun:test';

import type { TFailure } from '@/api/client';
import failureFixture from '@/mocks/failed_record_FAIL-001.fixture.json';
import { failureMeta } from './failure-meta';

const EXPECTED_REQUIREMENTS = ['Preserve account identifiers verbatim', 'Debits equal credits by branch', 'No silent value substitution'];

describe('failureMeta', () => {
  test('repeats canonical metadata for REQ-001 through REQ-009', () => {
    for (let requirementNumber = 1; requirementNumber <= 9; requirementNumber += 1) {
      const requirementId = `REQ-${String(requirementNumber).padStart(3, '0')}`;
      expect(failureMeta(requirementId).requirementText).toBe(EXPECTED_REQUIREMENTS[(requirementNumber - 1) % 3]);
    }
  });

  test.each(['malformed', 'REQ-000'])('uses failure-derived fallback for %s', (requirementId) => {
    const meta = failureMeta(requirementId, failureFixture as TFailure);

    expect(meta.title).toBe(failureFixture.field);
    expect(meta.meaning).toBe(failureFixture.expected);
    expect(meta.requirementText).toBe(requirementId);
  });

  test.each([
    ['REQ-004', 'tier'],
    ['REQ-005', 'interest'],
    ['REQ-006', 'currency'],
  ])('%s never renders the old %s copy', (requirementId, staleCopy) => {
    expect(JSON.stringify(failureMeta(requirementId)).toLowerCase()).not.toContain(staleCopy);
  });
});
