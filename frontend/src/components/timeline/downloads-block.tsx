import { useSuspenseQuery } from '@tanstack/react-query';
import { Download, ExternalLink } from 'lucide-react';
import type { TPatch } from '@/api/client';
import { traceabilityMatrixQuery } from '@/api/queries';
import { Dot } from '@/components/dot';
import { Button } from '@/components/ui/button';
import type { IDemo } from '@/lib/demos';
import { useRunUi } from '@/state/run-store';

interface IDownloadsBlockProps {
  demo: IDemo;
  patch: TPatch;
}

const downloadBlob = (filename: string, content: string, type: string): void => {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
};

const DownloadsBlock = ({ demo, patch }: IDownloadsBlockProps) => {
  const { data: matrix } = useSuspenseQuery(traceabilityMatrixQuery(demo.runId));
  const { approval } = useRunUi();
  const failureCount = matrix.reduce((total, row) => total + row.failure_ids.length, 0);

  return (
    <div className="rounded-lg border bg-card p-4 shadow-soft">
      {/* The whole run in one line, every number a contract object
       * from this page. */}
      <div className="mb-3 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
        <span className="font-mono font-semibold text-foreground">{matrix.length}</span> requirements
        <Dot />
        <span className="font-mono font-semibold text-foreground">{matrix.length}</span> tests
        <Dot />
        <span className="font-mono font-semibold text-foreground">{failureCount}</span> failures traced
        <Dot />
        <span className="font-mono font-semibold text-foreground">1</span> patch
        {!!approval && (
          <>
            <Dot />
            {approval.status} by <span className="font-mono font-semibold text-foreground">{approval.actor}</span>
          </>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button render={<a href={`/api/runs/${demo.runId}/evidence`} target="_blank" rel="noreferrer" />}>
          <ExternalLink aria-hidden="true" data-icon="inline-start" />
          Evidence pack
        </Button>
        <Button variant="outline" onClick={() => downloadBlob(`${patch.patch_id}.diff`, patch.diff, 'text/x-diff')}>
          <Download aria-hidden="true" data-icon="inline-start" />
          {patch.patch_id}.diff
        </Button>
        <Button
          variant="outline"
          onClick={() => downloadBlob(`${demo.runId}-matrix.json`, `${JSON.stringify(matrix, null, 2)}\n`, 'application/json')}
        >
          <Download aria-hidden="true" data-icon="inline-start" />
          matrix.json
        </Button>
        {demo.inputs.map((input) => (
          <Button key={input.name} variant="ghost" render={<a href={`/demo-inputs/${demo.id}/${input.name}`} download />}>
            <Download aria-hidden="true" data-icon="inline-start" />
            {input.name}
          </Button>
        ))}
      </div>
      <p className="mt-2.5 text-2xs text-faint-foreground">
        The evidence pack is served by FastAPI from the persisted run. The diff and matrix are the exact contract objects from this run.
      </p>
    </div>
  );
};

export { DownloadsBlock };
