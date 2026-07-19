import { PatchDiff } from '@pierre/diffs/react';
import { useState } from 'react';

import { type IDiffFile, mapFailuresToFiles, parsePatchFiles, splitPatch } from '@/lib/diff-hunks';
import { useTheme } from '@/lib/theme';
import { cn } from '@/lib/utils';
import { useRunUi } from '@/state/run-store';

type TDiffStyle = 'unified' | 'split';

interface IDiffViewerProps {
  patch: string;
  failureIds: string[];
  hoveredFailureId: string | null;
  onHoverFailure: (failureId: string | null) => void;
}

interface IFileHeaderProps {
  file: IDiffFile;
  failureIds: string[];
  hoveredFailureId: string | null;
  onHoverFailure: (failureId: string | null) => void;
  onOpenFailure: (failureId: string) => void;
}

const FileHeader = ({ file, failureIds, hoveredFailureId, onHoverFailure, onOpenFailure }: IFileHeaderProps) => {
  return (
    <div data-director-target="diff-file-header" className="flex items-center gap-2.5 border-b bg-card px-3.5 py-2">
      <span className="font-mono text-xs font-semibold">{file.path}</span>
      <span className="font-mono text-2xs">
        <span className="font-semibold text-success">+{file.additions}</span>{' '}
        <span className="font-semibold text-destructive">-{file.deletions}</span>
      </span>
      <div className="ml-auto flex gap-1.5">
        {failureIds.map((failureId) => (
          <button
            key={failureId}
            type="button"
            data-director-target="diff-failure"
            onClick={() => onOpenFailure(failureId)}
            onMouseEnter={() => onHoverFailure(failureId)}
            onMouseLeave={() => onHoverFailure(null)}
            onFocus={() => onHoverFailure(failureId)}
            onBlur={() => onHoverFailure(null)}
            className={cn(
              'rounded-4xl border border-destructive/30 bg-destructive-soft px-2 py-px font-mono text-4xs font-semibold text-destructive transition-all',
              hoveredFailureId === failureId && 'ring-2 ring-destructive/30',
            )}
          >
            {failureId}
          </button>
        ))}
      </div>
    </div>
  );
};

const DiffViewer = ({ patch, failureIds, hoveredFailureId, onHoverFailure }: IDiffViewerProps) => {
  const [diffStyle, setDiffStyle] = useState<TDiffStyle>('unified');
  const { theme } = useTheme();
  const { revealFailure } = useRunUi();

  const files = parsePatchFiles(patch);
  const failureFiles = mapFailuresToFiles(failureIds, files);
  const visibleSections = splitPatch(patch);

  const failuresForPath = (path: string): string[] => {
    return failureIds.filter((failureId) => failureFiles[failureId] === path);
  };

  return (
    <div data-director-target="diff-viewer" className="overflow-hidden rounded-lg border bg-card">
      <div className="flex items-center gap-2 border-b px-3.5 py-2">
        <span className="eyebrow">Files changed · {files.length}</span>
        <span className="ml-auto flex overflow-hidden rounded-md border text-3xs font-semibold">
          {(['unified', 'split'] as const).map((style) => (
            <button
              key={style}
              type="button"
              onClick={() => setDiffStyle(style)}
              className={cn('px-2.5 py-1 capitalize transition-colors', diffStyle === style ? 'bg-muted text-foreground' : 'text-faint-foreground')}
            >
              {style === 'unified' ? 'Stacked' : 'Split'}
            </button>
          ))}
        </span>
      </div>
      {visibleSections.map((section) => {
        const sectionFailures = failuresForPath(section.path);
        const highlighted = !!hoveredFailureId && sectionFailures.includes(hoveredFailureId);
        const file = files.find((candidate) => candidate.path === section.path) ?? { path: section.path, additions: 0, deletions: 0 };

        return (
          <div
            key={section.path}
            id={`diff-file-${section.path}`}
            data-director-target="diff-file"
            className={cn('transition-shadow', highlighted && 'shadow-[inset_0_0_0_2px_var(--destructive)]')}
          >
            <FileHeader
              file={file}
              failureIds={sectionFailures}
              hoveredFailureId={hoveredFailureId}
              onHoverFailure={onHoverFailure}
              onOpenFailure={(failureId) => revealFailure(failureId)}
            />
            <PatchDiff
              key={`${theme}-${diffStyle}`}
              patch={section.patch}
              disableWorkerPool
              options={{
                theme: { light: 'github-light-default', dark: 'github-dark-default' },
                themeType: theme,
                diffStyle,
                hunkSeparators: 'simple',
              }}
              renderCustomHeader={() => null}
            />
          </div>
        );
      })}
    </div>
  );
};

export { DiffViewer };
