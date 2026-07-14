import { useQuery } from '@tanstack/react-query';

import { runStatusQuery } from '@/api/queries';
import { Dot } from '@/components/dot';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { demoById } from '@/lib/demos';
import { cn } from '@/lib/utils';
import { useRunUi } from '@/state/run-store';

const TopBar = () => {
  const { demoId, reset } = useRunUi();
  const demo = demoId ? demoById(demoId) : undefined;
  const statusResult = useQuery({ ...runStatusQuery(demo?.runId ?? 'RUN-001'), enabled: !!demo });
  const runStatus = statusResult.data;

  return (
    <header className="flex items-center gap-3.5 border-b bg-surface-sunken px-5 py-2.5">
      <button type="button" onClick={reset} className="flex items-center gap-2.5">
        <span
          aria-hidden="true"
          className="relative size-[22px] rounded-md bg-[linear-gradient(135deg,#4338ca,#6d28d9)] after:absolute after:top-[3px] after:right-[3px] after:size-[5px] after:rounded-full after:bg-white after:ring-[1.5px] after:ring-[#4338ca] after:content-['']"
        />
        <span className="text-[15px] font-semibold tracking-display">Release Assurance</span>
      </button>
      {!!demo && !!runStatus && (
        <>
          <span className="h-[18px] w-px bg-input" aria-hidden="true" />
          <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2.5 py-1 font-mono text-2xs font-medium text-muted-foreground">
            {runStatus.run_id}
            <Dot />
            <span className="font-semibold text-warning">{runStatus.state}</span>
          </span>
          <Button size="xs" variant="ghost" onClick={reset}>
            New run
          </Button>
        </>
      )}
      <span className="ml-auto" />
      {!!demo && !!runStatus && (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-4xl px-3 py-1 font-mono text-3xs font-semibold uppercase tracking-eyebrow',
            runStatus.mode === 'fixture' ? 'bg-warning-soft text-warning' : 'bg-success-soft text-success',
          )}
        >
          <span
            aria-hidden="true"
            className={cn('size-1.5 rounded-full', runStatus.mode === 'fixture' ? 'animate-attn-pulse bg-warning-indicator' : 'bg-success-indicator')}
          />
          {runStatus.mode}
        </span>
      )}
      <span className="text-xs text-faint-foreground">demo_user</span>
      <ThemeToggle />
    </header>
  );
};

export { TopBar };
