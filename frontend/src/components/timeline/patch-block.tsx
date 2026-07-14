import type { TPatch } from '@/api/client';
import { DiffViewer } from '@/components/diff-viewer';
import { Dot } from '@/components/dot';
import { StatusChip } from '@/components/status-chip';

interface IPatchBlockProps {
  patch: TPatch;
  hoveredFailureId: string | null;
  onHoverFailure: (failureId: string | null) => void;
}

const PatchBlock = ({ patch, hoveredFailureId, onHoverFailure }: IPatchBlockProps) => {
  return (
    <div className="space-y-2.5">
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="font-mono text-xs font-semibold">{patch.patch_id}</span>
        <StatusChip status={patch.status} />
        <span className="inline-flex items-center gap-1.5 font-mono text-3xs text-faint-foreground">
          proposed by Codex
          <Dot />
          {patch.provenance.client}
          <Dot />
          fixes {patch.failure_ids.join(', ')}
        </span>
      </div>
      <DiffViewer patch={patch.diff} failureIds={patch.failure_ids} hoveredFailureId={hoveredFailureId} onHoverFailure={onHoverFailure} />
    </div>
  );
};

export { PatchBlock };
