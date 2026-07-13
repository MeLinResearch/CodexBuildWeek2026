import { ModelActionsPanel } from '@/components/model-actions-panel';
import { ThemeToggle } from '@/components/theme-toggle';
import { ApprovalGate } from '@/screens/approval-gate';
import { RecordDrilldown } from '@/screens/record-drilldown';
import { RunComparison } from '@/screens/run-comparison';
import { TraceabilityMatrix } from '@/screens/traceability-matrix';

const Application = () => {
  return (
    <main className="mx-auto flex w-full max-w-[1180px] flex-col gap-4 p-4 sm:p-6">
      <div className="flex min-h-8 justify-end">
        <ThemeToggle />
      </div>
      <ModelActionsPanel />
      <TraceabilityMatrix />
      <RecordDrilldown />
      <ApprovalGate />
      <RunComparison />
    </main>
  );
};

export { Application };
