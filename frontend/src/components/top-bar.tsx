import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from '@tanstack/react-router';
import { ShieldCheck } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useEffect, useState } from 'react';
import { runStatusQuery } from '@/api/queries';
import avatarMelinda from '@/assets/avatar-melinda.png';
import { Dot } from '@/components/dot';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { demoByRunId } from '@/lib/demos';
import { cn } from '@/lib/utils';
import { useRunUi } from '@/state/run-store';

/* Matches the content column on the start page. */
const HOME_WIDTH_PX = 880;

/* Amber marks the one state waiting on the human gate; decisions get
 * their outcome color, in-flight replay states read as active. */
const STATE_TONES: Record<string, string> = {
  PATCH_PENDING: 'text-warning',
  PATCH_APPROVED: 'text-success',
  PATCH_REJECTED: 'text-destructive',
};

const TopBar = () => {
  const shouldReduceMotion = useReducedMotion();
  const navigate = useNavigate();
  const { runId } = useParams({ strict: false });
  const { reset, approval, replayState } = useRunUi();
  const demo = runId ? demoByRunId(runId) : undefined;
  /* Falls back to RUN-001 on the start page so the mode pill (frozen
   * requirement: mode, sandbox policy, and validation status stay
   * visible on every screen) always has data behind it. */
  const statusResult = useQuery(runStatusQuery(demo?.runId ?? 'RUN-001'));
  const runStatus = statusResult.data;

  /* The chip follows the replay step by step, so it waits for the
   * timeline to publish a state instead of falling back to the run's
   * final fetched state (which would flash before CREATED on mount).
   * A recorded decision overrides the replay. */
  const decisionState = approval ? (approval.status === 'approved' ? 'PATCH_APPROVED' : 'PATCH_REJECTED') : null;
  const displayState = decisionState ?? replayState;

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
        className="relative mx-auto flex h-9 w-full items-center gap-3.5"
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
        {!!demo && !!displayState && (
          <span className="absolute left-1/2 inline-flex -translate-x-1/2 items-center gap-1.5 rounded-md bg-muted px-2.5 py-1 font-mono text-2xs font-medium text-muted-foreground">
            {demo.runId}
            <Dot />
            <AnimatePresence mode="popLayout" initial={false}>
              <motion.span
                key={displayState}
                initial={shouldReduceMotion ? false : { opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={shouldReduceMotion ? undefined : { opacity: 0, y: -5 }}
                transition={{ duration: 0.18 }}
                className={cn('font-semibold', STATE_TONES[displayState] ?? 'text-primary dark:text-primary-subtle')}
              >
                {displayState.replaceAll('_', ' ')}
              </motion.span>
            </AnimatePresence>
          </span>
        )}
        <span className="ml-auto" />
        {!!demo && (
          <Button size="xs" variant="ghost" onClick={handleNewRun}>
            New run
          </Button>
        )}
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
              {/* @pivanov: spec §2 wants actual GPT-5.6 call counts; the live
               * branch needs a real count once the backend exposes one. The
               * fixture count of live calls is honestly zero. */}
              Codex {runStatus.mode}, task {runStatus.mode === 'fixture' ? 'fixture' : runStatus.run_id}, sandbox read-only,{' '}
              {runStatus.mode === 'fixture' ? '0 live GPT-5.6 calls (fixture replay)' : 'GPT-5.6 calls live'}. All outputs schema-validated against
              the frozen contracts.
            </TooltipContent>
          </Tooltip>
        )}
        <span className="flex items-center gap-2">
          <img src={avatarMelinda} alt="" className="size-6 shrink-0 rounded-full border object-cover" />
          <span className="text-xs font-medium">Melinda Emerson</span>
        </span>
        <ThemeToggle />
      </motion.div>
    </header>
  );
};

export { TopBar };
