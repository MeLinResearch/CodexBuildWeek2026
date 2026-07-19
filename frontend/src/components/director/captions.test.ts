import { describe, expect, test } from 'bun:test';

import { buildTimedCaptionWords, captionWordIndexAt } from '@/components/director/captions';

describe('demo director timed captions', () => {
  test('maps every transcript word onto the real audio duration', () => {
    const words = buildTimedCaptionWords('Release Assurance catches silent failures.', 5);

    expect(words.map((word) => word.text)).toEqual(['Release', 'Assurance', 'catches', 'silent', 'failures.']);
    expect(words[0].startsAt).toBeGreaterThanOrEqual(0);
    expect(words.at(-1)?.endsAt).toBeLessThanOrEqual(5);

    for (let index = 1; index < words.length; index += 1) {
      expect(words[index].startsAt).toBe(words[index - 1].endsAt);
    }
  });

  test('gives punctuation additional display time', () => {
    const plain = buildTimedCaptionWords('steady steady', 3);
    const paused = buildTimedCaptionWords('steady, steady', 3);
    const plainFirstDuration = plain[0].endsAt - plain[0].startsAt;
    const pausedFirstDuration = paused[0].endsAt - paused[0].startsAt;

    expect(pausedFirstDuration).toBeGreaterThan(plainFirstDuration);
  });

  test('selects the active word from audio currentTime', () => {
    const words = buildTimedCaptionWords('one two three', 3);

    expect(captionWordIndexAt(words, 0)).toBe(0);
    expect(captionWordIndexAt(words, words[1].startsAt + 0.01)).toBe(1);
    expect(captionWordIndexAt(words, 99)).toBe(2);
    expect(captionWordIndexAt([], 0)).toBe(-1);
  });
});
