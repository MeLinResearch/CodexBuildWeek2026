import { describe, expect, it } from 'bun:test';
import { mapFailuresToFiles, parsePatchFiles, splitPatch } from '@/lib/diff-hunks';
import patchFixture from '@/mocks/patch_PATCH-001.fixture.json';

const MULTI_FILE_PATCH = [
  'diff --git a/reconcile/migration.py b/reconcile/migration.py',
  '--- a/reconcile/migration.py',
  '+++ b/reconcile/migration.py',
  '@@ -1 +1,2 @@',
  '-old = 1',
  '+new = 1',
  '+added = 2',
  'diff --git a/reconcile/parsers.py b/reconcile/parsers.py',
  '--- a/reconcile/parsers.py',
  '+++ b/reconcile/parsers.py',
  '@@ -1 +1 @@',
  '-return EPOCH_1900',
  '+raise DateParseError(value)',
].join('\n');

describe('parsePatchFiles', () => {
  it('parses the fixture patch into one file with counts', () => {
    const files = parsePatchFiles(patchFixture.diff);

    expect(files).toEqual([{ path: 'reconcile/migration.py', additions: 1, deletions: 1 }]);
  });

  it('parses multi-file patches with per-file counts', () => {
    const files = parsePatchFiles(MULTI_FILE_PATCH);

    expect(files).toEqual([
      { path: 'reconcile/migration.py', additions: 2, deletions: 1 },
      { path: 'reconcile/parsers.py', additions: 1, deletions: 1 },
    ]);
  });
});

describe('splitPatch', () => {
  it('round-trips a single-file patch', () => {
    const sections = splitPatch(patchFixture.diff);

    expect(sections).toHaveLength(1);
    expect(sections[0]?.path).toBe('reconcile/migration.py');
    expect(sections[0]?.patch.startsWith('diff --git')).toBe(true);
  });

  it('splits multi-file patches into per-file sections', () => {
    const sections = splitPatch(MULTI_FILE_PATCH);

    expect(sections.map((section) => section.path)).toEqual(['reconcile/migration.py', 'reconcile/parsers.py']);
    expect(sections[1]?.patch).toContain('DateParseError');
    expect(sections[1]?.patch).not.toContain('added = 2');
  });
});

describe('mapFailuresToFiles', () => {
  it('maps every failure to the single patched file', () => {
    const files = parsePatchFiles(patchFixture.diff);
    const mapping = mapFailuresToFiles(patchFixture.failure_ids, files);

    expect(mapping).toEqual({
      'FAIL-001': 'reconcile/migration.py',
      'FAIL-002': 'reconcile/migration.py',
      'FAIL-003': 'reconcile/migration.py',
    });
  });

  it('zips failures to files when counts match', () => {
    const files = parsePatchFiles(MULTI_FILE_PATCH);
    const mapping = mapFailuresToFiles(['FAIL-001', 'FAIL-003'], files);

    expect(mapping).toEqual({
      'FAIL-001': 'reconcile/migration.py',
      'FAIL-003': 'reconcile/parsers.py',
    });
  });

  it('degrades to no mapping when counts are ambiguous', () => {
    const files = parsePatchFiles(MULTI_FILE_PATCH);

    expect(mapFailuresToFiles(['FAIL-001', 'FAIL-002', 'FAIL-003'], files)).toEqual({});
  });
});
