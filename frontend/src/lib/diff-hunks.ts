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
export { mapFailuresToFiles, parsePatchFiles, splitPatch };
