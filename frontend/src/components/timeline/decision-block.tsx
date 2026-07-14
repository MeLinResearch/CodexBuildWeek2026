import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { api, type TPatch } from '@/api/client';
import { StatusChip } from '@/components/status-chip';
import { Button } from '@/components/ui/button';
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { useRunUi } from '@/state/run-store';

/* Matches the signed-in identity shown in the header. */
const DEMO_ACTOR = 'melinda.emerson';

type TDecision = 'approve' | 'reject';

interface IDecisionBlockProps {
  runId: string;
  patch: TPatch;
}

const DecisionBlock = ({ runId, patch }: IDecisionBlockProps) => {
  const queryClient = useQueryClient();
  const { approval, recordApproval } = useRunUi();
  const [decision, setDecision] = useState<TDecision | null>(null);
  const [note, setNote] = useState('');

  /* A decision can move the run to an active state (approve requests
   * the rerun), so the status query refetches once; if the backend
   * really moved, its refetchInterval resumes polling on its own. */
  const resumeStatusPolling = (): void => {
    queryClient.invalidateQueries({ queryKey: ['runs', runId, 'status'] });
  };

  const approveMutation = useMutation({
    mutationFn: async (approvalNote: string) => {
      const result = await api.approvePatch(patch.patch_id, DEMO_ACTOR, approvalNote);
      const rerun = await api.rerun(runId);
      return { result, rerun };
    },
    onSuccess: ({ result }) => {
      recordApproval({ status: 'approved', actor: result.actor, note: result.note });
      resumeStatusPolling();
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (approvalNote: string) => {
      return api.rejectPatch(patch.patch_id, DEMO_ACTOR, approvalNote);
    },
    onSuccess: (result) => {
      recordApproval({ status: 'rejected', actor: result.actor, note: result.note });
      resumeStatusPolling();
    },
  });

  const busy = approveMutation.isPending || rejectMutation.isPending;
  const isApprove = decision === 'approve';

  const openDecision = (next: TDecision): void => {
    setNote('');
    setDecision(next);
  };

  const confirmDecision = (): void => {
    const trimmed = note.trim();

    if (!trimmed) {
      return;
    }

    if (isApprove) {
      approveMutation.mutate(trimmed);
    } else {
      rejectMutation.mutate(trimmed);
    }
  };

  if (approval) {
    return (
      <div className="rounded-lg border bg-card p-4 shadow-soft">
        <div className="flex flex-wrap items-center gap-2.5 text-sm">
          <StatusChip status={approval.status} />
          <span className="text-muted-foreground">
            {patch.patch_id} {approval.status} by <span className="font-mono text-xs font-medium text-foreground">{approval.actor}</span>, recorded in
            the audit trail
          </span>
        </div>
        {!!approval.note && <p className="mt-2 border-l-2 border-border pl-3 text-xs text-muted-foreground italic">"{approval.note}"</p>}
        <p className="mt-2.5 text-2xs text-faint-foreground">
          {approval.status === 'approved'
            ? 'Rerun accepted. The live pipeline will apply the patch in a sandbox, rerun the tests, and produce the evidence pack; this fixture run stays at PATCH_PENDING.'
            : 'The run returns to TRIAGED. Rejected patches never rerun.'}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-primary/35 bg-card p-4 shadow-lift ring-2 ring-primary/10">
      <div className="flex items-center gap-2.5">
        <span aria-hidden="true" className="size-2 rounded-full bg-primary animate-attn-pulse dark:bg-primary-subtle" />
        <h3 className="text-[15px] font-medium tracking-display">Waiting for your decision</h3>
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">
        Codex proposes. <span className="font-medium text-primary dark:text-primary-subtle">You approve.</span> Nothing ships without you.
      </p>
      <div className="mt-3 flex items-center gap-2.5">
        <Button disabled={busy} onClick={() => openDecision('approve')}>
          {approveMutation.isPending ? 'Recording…' : 'Approve patch'}
        </Button>
        <Button
          variant="outline"
          disabled={busy}
          className="text-destructive hover:bg-destructive-soft hover:text-destructive"
          onClick={() => openDecision('reject')}
        >
          {rejectMutation.isPending ? 'Recording…' : 'Reject patch'}
        </Button>
      </div>
      <p className="mt-2.5 text-2xs text-faint-foreground">Every decision is recorded with a note under {DEMO_ACTOR} in the audit trail.</p>
      {(approveMutation.isError || rejectMutation.isError) && (
        <p className="mt-2 text-2xs text-destructive">The decision endpoint did not respond; try again.</p>
      )}
      <Dialog
        open={decision !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDecision(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {isApprove ? 'Approve' : 'Reject'} {patch.patch_id}
            </DialogTitle>
            <DialogDescription>
              {isApprove
                ? `A note is required: approvals are part of the audit trail. Approving records ${DEMO_ACTOR} and requests the rerun.`
                : 'A note is required: rejections are part of the audit trail. The run returns to TRIAGED and the patch never reruns.'}
            </DialogDescription>
          </DialogHeader>
          <Textarea
            placeholder={isApprove ? 'Why is this patch approved?' : 'Why is this patch rejected?'}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
          <DialogFooter>
            <DialogClose render={<Button variant="ghost">Cancel</Button>} />
            <DialogClose
              render={
                <Button variant={isApprove ? 'default' : 'destructive'} disabled={note.trim() === ''} onClick={confirmDecision}>
                  {isApprove ? 'Approve patch' : 'Reject patch'}
                </Button>
              }
            />
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export { DecisionBlock };
