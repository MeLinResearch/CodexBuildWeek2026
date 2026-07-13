import { describe, expect, test } from 'bun:test';

import { resolveTheme } from '@/lib/theme-preference';

describe('resolveTheme', () => {
  test('uses a stored theme', () => {
    expect(resolveTheme('light', true)).toBe('light');
    expect(resolveTheme('dark', false)).toBe('dark');
  });

  test('falls back to the system preference', () => {
    expect(resolveTheme(null, false)).toBe('light');
    expect(resolveTheme(null, true)).toBe('dark');
  });

  test('ignores invalid stored values', () => {
    expect(resolveTheme('sepia', false)).toBe('light');
  });
});
