import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from '@tanstack/react-router';
import { ShieldCheck } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { useEffect, useState } from 'react';

import { runStatusQuery } from '@/api/queries';
import { Dot } from '@/components/dot';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { demoByRunId } from '@/lib/demos';
import { cn } from '@/lib/utils';
import { useRunUi } from '@/state/run-store';

/* Matches the content column on the start page. */
const HOME_WIDTH_PX = 880;

const TopBar = () => {
  const shouldReduceMotion = useReducedMotion();
  const navigate = useNavigate();
  const { runId } = useParams({ strict: false });
  const { reset } = useRunUi();
  const demo = runId ? demoByRunId(runId) : undefined;
  /* Falls back to RUN-001 on the start page so the mode pill (frozen
   * requirement: mode, sandbox policy, and validation status stay
   * visible on every screen) always has data behind it. */
  const statusResult = useQuery(runStatusQuery(demo?.runId ?? 'RUN-001'));
  const runStatus = statusResult.data;

  /* The header hugs the content column on the start page and widens
   * to the viewport on a run page. maxWidth animates in pixels because
   * motion cannot interpolate between mixed units like 880px and 100%. */
  const [viewportWidth, setViewportWidth] = useState(() => window.innerWidth);

  useEffect(() => {
    const handleResize = (): void => {
      setViewportWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const handleNewRun = (): void => {
    reset();
    navigate({ to: '/' });
  };

  return (
    <header className="sticky top-0 z-30 px-6 py-3.5 backdrop-blur-xl">
      <motion.div
        className="mx-auto flex h-9 w-full items-center gap-3.5"
        initial={false}
        animate={{ maxWidth: demo ? viewportWidth : HOME_WIDTH_PX }}
        transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <Link to="/" onClick={reset} className="group/brand flex items-center gap-2.5">
          <span
            aria-hidden="true"
            className="grid size-7 place-items-center rounded-sm bg-primary text-primary-foreground shadow-soft transition-transform duration-500 ease-fluid group-hover/brand:scale-105"
          >
            <ShieldCheck className="size-5" />
          </span>
          <span className="text-base font-semibold tracking-tight">Release Assurance</span>
        </Link>
        {!!demo && !!runStatus && (
          <>
            <span className="h-[18px] w-px bg-input" aria-hidden="true" />
            <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2.5 py-1 font-mono text-2xs font-medium text-muted-foreground">
              {runStatus.run_id}
              <Dot />
              <span className="font-semibold text-warning">{runStatus.state}</span>
            </span>
            <Button size="xs" variant="ghost" onClick={handleNewRun}>
              New run
            </Button>
          </>
        )}
        <span className="ml-auto" />
        {!!runStatus && (
          <Tooltip>
            <TooltipTrigger
              render={
                <span
                  className={cn(
                    'inline-flex cursor-default items-center gap-1.5 rounded-4xl px-3 py-1 font-mono text-3xs font-semibold uppercase tracking-eyebrow',
                    runStatus.mode === 'fixture' ? 'bg-warning-soft text-warning' : 'bg-success-soft text-success',
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      'size-1.5 rounded-full',
                      runStatus.mode === 'fixture' ? 'animate-attn-pulse bg-warning-indicator' : 'bg-success-indicator',
                    )}
                  />
                  {runStatus.mode}
                </span>
              }
            />
            <TooltipContent>
              Codex {runStatus.mode}, task {runStatus.mode === 'fixture' ? 'fixture' : runStatus.run_id}, sandbox read-only, GPT-5.6 calls{' '}
              {runStatus.mode === 'fixture' ? 'fixture' : 'live'}. All outputs schema-validated against the frozen contracts.
            </TooltipContent>
          </Tooltip>
        )}
        <span className="text-xs text-faint-foreground">demo_user</span>
        <ThemeToggle />
      </motion.div>
    </header>
  );
};

export { TopBar };
