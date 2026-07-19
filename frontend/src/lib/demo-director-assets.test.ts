import { describe, expect, test } from 'bun:test';
import { readFile } from 'node:fs/promises';

const INDEX_HTML_URL = new URL('../../index.html', import.meta.url);
const DIRECTOR_AVATARS = ['avatar-melinda.png', 'avatar-codex.png', 'avatar-pivanov.png'];

describe('demo director avatar loading', () => {
  test('preloads every avatar before the Space-triggered overlay is created', async () => {
    const indexHtml = await readFile(INDEX_HTML_URL, 'utf8');

    for (const avatar of DIRECTOR_AVATARS) {
      expect(indexHtml).toContain(`rel="preload" as="image" type="image/png" href="/src/assets/${avatar}"`);
    }
  });
});
