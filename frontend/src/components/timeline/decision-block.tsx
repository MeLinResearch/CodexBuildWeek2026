import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';

import { api, type TPatch } from '@/api/client';
import { StatusChip } from '@/components/status-chip';
import { Button } from '@/components/ui/button';
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useRunUi } from '@/state/run-store';

const DEMO_ACTOR = 'demo_user';

interface IDecisionBlockProps {
  runId: string;
  patch: TPatch;
}

const DecisionBlock = ({ runId, patch }: IDecisionBlockProps) => {
  const { approval, recordApproval } = useRunUi();
  const [note, setNote] = useState('');
  const [rejectNote, setRejectNote] = useState('');
  const [rejectOpen, setRejectOpen] = useState(false);

  const approveMutation = useMutation({
    mutationFn: async (approvalNote: string | null) => {
      const result = await api.approvePatch(patch.patch_id, DEMO_ACTOR, approvalNote);
      const rerun = await api.rerun(runId);
      return { result, rerun };
    },
    onSuccess: ({ result }) => {
      recordApproval({ status: 'approved', actor: result.actor, note: result.note });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (approvalNote: string | null) => {
      return api.rejectPatch(patch.patch_id, DEMO_ACTOR, approvalNote);
    },
    onSuccess: (result) => {
      recordApproval({ status: 'rejected', actor: result.actor, note: result.note });
    },
  });

  const busy = approveMutation.isPending || rejectMutation.isPending;

  /* A note typed in the main input counts as the rejection note; the
   * dialog only appears when there is nothing to record yet. */
  const handleReject = (): void => {
    const trimmed = note.trim();

    if (trimmed) {
      rejectMutation.mutate(trimmed);
      return;
    }

    setRejectNote('');
    setRejectOpen(true);
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
    <div className="rounded-lg border bg-card p-3.5 shadow-soft">
      <div className="flex items-center gap-2.5">
        <Input
          placeholder="Approval note (optional, recorded in the audit trail)"
          value={note}
          disabled={busy}
          onChange={(event) => setNote(event.target.value)}
        />
        <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
          <Button
            variant="outline"
            disabled={busy}
            className="text-destructive hover:bg-destructive-soft hover:text-destructive"
            onClick={handleReject}
          >
            Reject
          </Button>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Reject {patch.patch_id}</DialogTitle>
              <DialogDescription>
                A note is required: rejections are part of the audit trail. The run returns to TRIAGED and the patch never reruns.
              </DialogDescription>
            </DialogHeader>
            <Textarea placeholder="Why is this patch rejected?" value={rejectNote} onChange={(event) => setRejectNote(event.target.value)} />
            <DialogFooter>
              <DialogClose render={<Button variant="ghost">Cancel</Button>} />
              <DialogClose
                render={
                  <Button variant="destructive" disabled={rejectNote.trim() === ''} onClick={() => rejectMutation.mutate(rejectNote.trim() || null)}>
                    Reject patch
                  </Button>
                }
              />
            </DialogFooter>
          </DialogContent>
        </Dialog>
        <Button disabled={busy} onClick={() => approveMutation.mutate(note.trim() || null)}>
          {approveMutation.isPending ? 'Recording…' : 'Approve patch'}
        </Button>
      </div>
      <p className="mt-2 text-2xs text-faint-foreground">
        Nothing is applied without you. Approving records {DEMO_ACTOR} in the audit trail and requests the rerun.
      </p>
      {(approveMutation.isError || rejectMutation.isError) && (
        <p className="mt-2 text-2xs text-destructive">The decision endpoint did not respond; try again.</p>
      )}
    </div>
  );
};

export { DecisionBlock };
