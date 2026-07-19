interface IDiffFile {
  path: string;
  additions: number;
  deletions: number;
}

const parsePatchFiles = (patch: string): IDiffFile[] => {
  const files: IDiffFile[] = [];
  let current: IDiffFile | null = null;

  for (const line of patch.split('\n')) {
    const header = line.match(/^diff --git a\/.+ b\/(.+)$/);

    if (header?.[1]) {
      current = { path: header[1], additions: 0, deletions: 0 };
      files.push(current);
      continue;
    }

    if (!current) {
      continue;
    }

    if (line.startsWith('+') && !line.startsWith('+++')) {
      current.additions += 1;
    }

    if (line.startsWith('-') && !line.startsWith('---')) {
      current.deletions += 1;
    }
  }

  return files;
};

/* Maps each failure to the file its fix lives in. The contract gives
 * a patch only failure_ids and a diff, so the mapping is heuristic:
 * a single-file patch covers every failure; a patch with exactly one
 * file per failure zips by order; anything else stays unmapped and
 * the UI degrades to showing the file list without per-failure chips. */
const mapFailuresToFiles = (failureIds: string[], files: IDiffFile[]): Record<string, string> => {
  if (files.length === 1 && files[0]) {
    const path = files[0].path;
    return Object.fromEntries(failureIds.map((failureId) => [failureId, path]));
  }

  if (files.length === failureIds.length) {
    return Object.fromEntries(failureIds.map((failureId, index) => [failureId, files[index]?.path ?? '']));
  }

  return {};
};

interface IFilePatch {
  path: string;
  patch: string;
}

const HUNK_HEADER = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$/;

const compactHunk = (header: string, body: string[], contextLines: number): string[] => {
  const match = header.match(HUNK_HEADER);

  if (!match?.[1] || !match[3]) {
    return [header, ...body];
  }

  const changedIndexes = body.flatMap((line, index) => (line.startsWith('+') || line.startsWith('-') ? [index] : []));

  if (changedIndexes.length === 0) {
    return [header, ...body];
  }

  const ranges: Array<{ start: number; end: number }> = [];
  for (const index of changedIndexes) {
    const start = Math.max(0, index - contextLines);
    const end = Math.min(body.length - 1, index + contextLines);
    const previous = ranges.at(-1);

    if (previous && start <= previous.end + 1) {
      previous.end = Math.max(previous.end, end);
    } else {
      ranges.push({ start, end });
    }
  }

  const originalOldStart = Number(match[1]);
  const originalNewStart = Number(match[3]);
  const suffix = match[5] ?? '';

  const positionAt = (targetIndex: number): { oldLine: number; newLine: number } => {
    let oldLine = originalOldStart;
    let newLine = originalNewStart;

    for (const line of body.slice(0, targetIndex)) {
      if (line.startsWith('-')) {
        oldLine += 1;
      } else if (line.startsWith('+')) {
        newLine += 1;
      } else if (!line.startsWith('\\')) {
        oldLine += 1;
        newLine += 1;
      }
    }

    return { oldLine, newLine };
  };

  return ranges.flatMap(({ start, end }) => {
    const lines = body.slice(start, end + 1);
    const { oldLine, newLine } = positionAt(start);
    const oldCount = lines.filter((line) => !line.startsWith('+') && !line.startsWith('\\')).length;
    const newCount = lines.filter((line) => !line.startsWith('-') && !line.startsWith('\\')).length;
    return [`@@ -${oldLine},${oldCount} +${newLine},${newCount} @@${suffix}`, ...lines];
  });
};

const compactPatchContext = (patch: string, contextLines = 3): string => {
  const output: string[] = [];
  const lines = patch.split('\n');

  /* split() adds an empty sentinel for the patch's final newline. It
   * is not a unified-diff context line (real blank context is " "),
   * so do not let it inflate a compacted hunk's line counts. */
  if (lines.at(-1) === '') {
    lines.pop();
  }

  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? '';

    if (!line.startsWith('@@ ')) {
      output.push(line);
      index += 1;
      continue;
    }

    const body: string[] = [];
    let nextIndex = index + 1;
    while (nextIndex < lines.length && !lines[nextIndex]?.startsWith('@@ ') && !lines[nextIndex]?.startsWith('diff --git ')) {
      body.push(lines[nextIndex] ?? '');
      nextIndex += 1;
    }
    output.push(...compactHunk(line, body, Math.max(0, contextLines)));
    index = nextIndex;
  }

  return output.join('\n');
};

const splitPatch = (patch: string): IFilePatch[] => {
  const sections: IFilePatch[] = [];
  const lines = patch.split('\n');
  let currentLines: string[] = [];
  let currentPath: string | null = null;

  const flush = (): void => {
    if (currentPath && currentLines.length > 0) {
      sections.push({ path: currentPath, patch: currentLines.join('\n') });
    }
  };

  for (const line of lines) {
    const header = line.match(/^diff --git a\/.+ b\/(.+)$/);

    if (header?.[1]) {
      flush();
      currentPath = header[1];
      currentLines = [line];
      continue;
    }

    currentLines.push(line);
  }

  flush();
  return sections;
};

export type { IDiffFile };
export { compactPatchContext, mapFailuresToFiles, parsePatchFiles, splitPatch };
