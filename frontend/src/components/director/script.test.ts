import { describe, expect, it } from 'bun:test';

import { DIRECTOR_APPROVAL_NOTE, FALLBACK_LINES, INTRO_LINES, isDirectorSpaceKey, isDirectorTurn } from '@/components/director/script';

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
    const fallbackWords = Object.entries(FALLBACK_LINES)
      .filter(([phase]) => phase !== 'intro')
      .flatMap(([, lines]) => lines)
      .reduce((total, line) => total + line.text.split(/\s+/).length, 0);
    const introWords = INTRO_LINES.reduce((total, line) => total + line.text.split(/\s+/).length, 0);

    expect(Object.keys(FALLBACK_LINES)).toHaveLength(10);
    expect(fallbackWords).toBeLessThan(190);
    expect(introWords).toBeLessThan(90);
    expect(INTRO_LINES.map((line) => line.speaker)).toEqual(['pivanov', 'codex', 'melinda', 'melinda', 'codex']);
    expect(INTRO_LINES.find((line) => line.text.includes('welcome to Release Assurance'))?.speaker).toBe('melinda');
    expect(FALLBACK_LINES.intro).toBe(INTRO_LINES);
    expect(FALLBACK_LINES.requirements.map((line) => line.speaker)).toEqual(['pivanov', 'codex']);
    expect(FALLBACK_LINES.failures.map((line) => line.speaker)).toEqual(['melinda', 'codex']);
    expect(FALLBACK_LINES.traceability.map((line) => line.speaker)).toEqual(['pivanov', 'codex']);
    expect(FALLBACK_LINES.review.map((line) => line.speaker)).toEqual(['pivanov', 'codex', 'melinda']);
    expect(FALLBACK_LINES.approval.map((line) => line.speaker)).toEqual(['melinda', 'melinda']);
    expect(FALLBACK_LINES.evidence.map((line) => line.speaker)).toEqual(['melinda', 'codex']);
    expect(DIRECTOR_APPROVAL_NOTE).toContain('Reviewed the complete diff');
  });
});
