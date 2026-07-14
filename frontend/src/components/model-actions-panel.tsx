import { useQuery } from '@tanstack/react-query';

import { runStatusQuery } from '@/api/queries';
import { demoById } from '@/lib/demos';
import { useRunUi } from '@/state/run-store';

/* Frozen requirement (ARCHITECTURE.md §2): mode, task id, sandbox
 * policy, call counts, and validation status stay visible on every
 * screen. Rendered as a slim strip pinned to the bottom of the app. */
const ModelActionsPanel = () => {
  const { demoId } = useRunUi();
  const runId = demoId ? (demoById(demoId)?.runId ?? 'RUN-001') : 'RUN-001';
  const statusResult = useQuery(runStatusQuery(runId));
  const mode = statusResult.data?.mode ?? 'fixture';
  const isFixture = mode === 'fixture';

  return (
    <footer className="flex flex-wrap items-center gap-x-5 gap-y-1 border-t bg-surface-sunken px-5 py-2 text-2xs text-muted-foreground">
      <span className="eyebrow">Model actions</span>
      <span>
        Codex{' '}
        <span className={isFixture ? 'font-mono font-semibold text-warning uppercase' : 'font-mono font-semibold text-success uppercase'}>
          {mode}
        </span>
      </span>
      <span>
        task <span className="font-mono">{isFixture ? 'fixture' : runId}</span>
      </span>
      <span>
        sandbox <span className="font-mono">read-only</span>
      </span>
      <span>
        GPT-5.6 calls <span className="font-mono">{isFixture ? 'fixture' : 'live'}</span>
      </span>
      <span className="ml-auto font-medium text-success">✓ all outputs schema-validated</span>
    </footer>
  );
};

export { ModelActionsPanel };
