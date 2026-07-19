import { describe, expect, it } from 'bun:test';

import { DIRECTOR_APPROVAL_NOTE, FALLBACK_LINES, isDirectorSpaceKey, isDirectorTurn } from '@/lib/demo-director-script';

const spaceEvent = {
  code: 'Space',
  repeat: false,
  altKey: false,
  ctrlKey: false,
  metaKey: false,
  shiftKey: false,
};

describe('demo director browser contract', () => {
  it('accepts only an unmodified, non-repeated Space press', () => {
    expect(isDirectorSpaceKey(spaceEvent)).toBe(true);
    expect(isDirectorSpaceKey({ ...spaceEvent, repeat: true })).toBe(false);
    expect(isDirectorSpaceKey({ ...spaceEvent, code: 'Enter' })).toBe(false);
    expect(isDirectorSpaceKey({ ...spaceEvent, shiftKey: true })).toBe(false);
    expect(isDirectorSpaceKey({ ...spaceEvent, metaKey: true })).toBe(false);
  });

  it('accepts only small schema-shaped runtime turns', () => {
    expect(
      isDirectorTurn({
        lines: [{ speaker: 'codex', text: 'I prepared a read-only patch proposal for human review.' }],
      }),
    ).toBe(true);
    expect(isDirectorTurn({ lines: [] })).toBe(false);
    expect(isDirectorTurn({ lines: [{ speaker: 'unknown', text: 'No.' }] })).toBe(false);
    expect(isDirectorTurn({ lines: [{ speaker: 'melinda', text: '' }] })).toBe(false);
    expect(
      isDirectorTurn({
        lines: [
          { speaker: 'melinda', text: 'One.' },
          { speaker: 'pivanov', text: 'Two.' },
          { speaker: 'codex', text: 'Three.' },
          { speaker: 'melinda', text: 'Four.' },
        ],
      }),
    ).toBe(false);
  });

  it('keeps only concise emergency fallbacks hardcoded', () => {
    const fallbackWords = Object.values(FALLBACK_LINES)
      .flat()
      .reduce((total, line) => total + line.text.split(/\s+/).length, 0);

    expect(Object.keys(FALLBACK_LINES)).toHaveLength(9);
    expect(fallbackWords).toBeLessThan(140);
    expect(DIRECTOR_APPROVAL_NOTE).toContain('Reviewed the complete diff');
  });
});
