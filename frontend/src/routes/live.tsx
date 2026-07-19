import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useEffect, useRef, useState } from 'react';

import { api } from '@/api/client';
import { Dot } from '@/components/dot';
import { AgentStep } from '@/components/timeline/agent-step';
import { Button } from '@/components/ui/button';
import { useRunUi } from '@/state/run-store';

/* The live run is one long POST, so the run id (and with it the real
 * timeline route) only exists when the pipeline finishes. This route
 * is the honest in-between: it looks like the run screen with the
 * first step thinking, starts the POST on mount, and replaces itself
 * with /$runId the moment the pipeline returns. */
const LiveRunView = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { beginRun } = useRunUi();
  const refStarted = useRef(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const liveRunMutation = useMutation({
    mutationFn: () => api.createLiveRun(),
    onSuccess: (result) => {
      queryClient.removeQueries({ queryKey: ['runs', result.run_id] });
      beginRun();
      navigate({ to: '/$runId', params: { runId: result.run_id }, replace: true });
    },
  });
  const { mutate: startLiveRun } = liveRunMutation;

  useEffect(() => {
    if (refStarted.current) {
      return;
    }

    refStarted.current = true;
    startLiveRun();
  }, [startLiveRun]);

  useEffect(() => {
    const startedAt = performance.now();
    const interval = window.setInterval(() => {
      setElapsedSeconds(Math.floor((performance.now() - startedAt) / 1000));
    }, 500);
    return () => {
      window.clearInterval(interval);
    };
  }, []);

  if (liveRunMutation.isError) {
    return (
      <div className="mx-auto w-full max-w-[880px] pb-10">
        <div className="rounded-lg border bg-destructive-soft p-4">
          <p className="text-sm font-medium text-destructive">The FastAPI demo runtime did not start the run.</p>
          <p className="mt-1 text-xs text-muted-foreground">
            The uvicorn console has the full cause chain. Fix the runtime, then start a fresh live run.
          </p>
          <Button size="sm" variant="outline" className="mt-3" onClick={() => navigate({ to: '/' })}>
            Back to start
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-[880px] pb-10">
      <div className="mb-6">
        <div className="eyebrow flex items-center gap-1.5">
          live run
          <Dot />
          GPT-5.6 + Codex
        </div>
        <h2 className="mt-1 text-[22px] font-medium tracking-display">
          Core banking migration, <span className="grad">running live</span>
        </h2>
      </div>

      <AgentStep title="Ingesting artifacts" activity="Registering the spec, source data, and target schema" status="thinking" />

      <p className="pl-9 text-xs leading-relaxed text-muted-foreground">
        GPT-5.6 extracts the control manifest, the deterministic tests run against the migrated records, and Codex proposes a patch in a read-only
        sandbox. Usually under two minutes. <span className="ml-1 font-mono text-faint-foreground tabular-nums">{elapsedSeconds}s</span>
      </p>
    </div>
  );
};

export const Route = createFileRoute('/live')({
  component: LiveRunView,
});
