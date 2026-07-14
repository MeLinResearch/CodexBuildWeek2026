import { useSuspenseQuery } from '@tanstack/react-query';
import { Download, ExternalLink } from 'lucide-react';
import type { TPatch } from '@/api/client';
import { traceabilityMatrixQuery } from '@/api/queries';
import { Button } from '@/components/ui/button';
import type { IDemo } from '@/lib/demos';

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

  return (
    <div className="rounded-lg border bg-card p-4 shadow-soft">
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
        The evidence pack is served by the fixture API; the diff and matrix are the exact contract objects from this run.
      </p>
    </div>
  );
};

export { DownloadsBlock };
