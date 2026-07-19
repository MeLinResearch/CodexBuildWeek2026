import { useSuspenseQuery } from '@tanstack/react-query';
import { ArrowDown } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';

import { patchesQuery, runStatusQuery, traceabilityMatrixQuery } from '@/api/queries';
import { directorTimelineIsControlled, type IStepTiming, useTimelineSequence } from '@/components/director/timeline-sequence';
import { Dot } from '@/components/dot';
import { type IMinimapStep, StepMinimap } from '@/components/step-minimap';
import { AgentStep } from '@/components/timeline/agent-step';
import { DecisionBlock } from '@/components/timeline/decision-block';
import { DownloadsBlock } from '@/components/timeline/downloads-block';
import { IngestBlock } from '@/components/timeline/ingest-block';
import { MatrixBlock } from '@/components/timeline/matrix-block';
import { PatchBlock } from '@/components/timeline/patch-block';
import { RequirementsBlock } from '@/components/timeline/requirements-block';
import { TestsBlock } from '@/components/timeline/tests-block';
import { Button } from '@/components/ui/button';
import type { IDemo } from '@/lib/demos';
import { mapFailuresToFiles, parsePatchFiles } from '@/lib/diff-hunks';
import { useRunStateSync } from '@/lib/use-run-state-sync';
import { cn } from '@/lib/utils';
import { type TReplayState, useRunUi } from '@/state/run-store';

/* Paced for a human watching: each step thinks with a spinner first,
 * then its results hold long enough to actually read. */
const STEP_TIMINGS: IStepTiming[] = [
  { thinkMs: 1400, readMs: 3600 },
  { thinkMs: 1600, readMs: 2600 },
  { thinkMs: 1400, readMs: 3000 },
  { thinkMs: 1800, readMs: 4800 },
  { thinkMs: 2000, readMs: 4600 },
];

/* Contract run state reached once N steps have landed their results;
 * the header chip walks through these as the replay advances. The
 * tests step covers generation and execution, so it lands EXECUTED. */
const REPLAY_STATES: TReplayState[] = ['CREATED', 'INGESTED', 'MANIFEST_READY', 'EXECUTED', 'TRIAGED', 'PATCH_PENDING'];

const FOLLOW_THRESHOLD_PX = 140;

interface IRunTimelineProps {
  demo: IDemo;
  refScroll: React.RefObject<HTMLElement | null>;
}

const RunTimeline = ({ demo, refScroll }: IRunTimelineProps) => {
  const shouldReduceMotion = useReducedMotion();
  const { droppedFiles, approval, setReplayState } = useRunUi();
  const { data: matrix } = useSuspenseQuery(traceabilityMatrixQuery(demo.runId));
  const { data: patches } = useSuspenseQuery(patchesQuery(demo.runId));
  const { data: runStatus } = useSuspenseQuery(runStatusQuery(demo.runId));
  useRunStateSync(demo.runId);

  const [hoveredFailureId, setHoveredFailureId] = useState<string | null>(null);
  const directorControlled = directorTimelineIsControlled();
  const { statusFor, finished } = useTimelineSequence(STEP_TIMINGS, !!shouldReduceMotion, directorControlled);

  const refEnd = useRef<HTMLDivElement>(null);
  const refFollowing = useRef(true);
  const [stepsBelow, setStepsBelow] = useState(0);
  const [gatePinned, setGatePinned] = useState(false);

  /* The end sentinel doubles as a pinned-detector: while it sits
   * below the viewport the gate card is floating, and gets a fade
   * halo so content dissolves under it instead of hard-clipping.
   * Docked (sentinel visible), the halo would wash out the step
   * title, so it fades away. */
  useEffect(() => {
    const sentinel = refEnd.current;
    const root = refScroll.current;

    if (!sentinel || !root || !finished || approval) {
      setGatePinned(false);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        setGatePinned(!entry.isIntersecting);
      },
      { root },
    );
    observer.observe(sentinel);
    return () => {
      observer.disconnect();
    };
  }, [finished, approval, refScroll]);

  /* Autoscroll follows only until the user scrolls up to read; new
   * steps then queue behind the pill. Follow-state is keyed to wheel
   * gestures (not scroll position) so an in-flight smooth autoscroll
   * landing at the bottom cannot re-enable following on its own. */
  useEffect(() => {
    const container = refScroll.current;

    if (!container) {
      return;
    }

    const handleWheel = (event: WheelEvent): void => {
      if (event.deltaY < 0) {
        refFollowing.current = false;
        return;
      }

      requestAnimationFrame(() => {
        const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < FOLLOW_THRESHOLD_PX;

        if (nearBottom) {
          refFollowing.current = true;
          setStepsBelow(0);
        }
      });
    };

    container.addEventListener('wheel', handleWheel, { passive: true });
    return () => {
      container.removeEventListener('wheel', handleWheel);
    };
  }, [refScroll]);

  const stepsRevealed = STEP_TIMINGS.filter((_, index) => statusFor(index) === 'reading' || statusFor(index) === 'done').length;
  const revealedCount = stepsRevealed + (finished ? 1 : 0) + (approval ? 1 : 0);

  /* Layout effect so the chip never paints the run's final state
   * before the replay resets it to CREATED on mount. */
  useLayoutEffect(() => {
    setReplayState(REPLAY_STATES[stepsRevealed] ?? 'PATCH_PENDING');
  }, [stepsRevealed, setReplayState]);

  const scrollViewportToEnd = useCallback((): void => {
    const viewport = refScroll.current;

    if (!viewport) {
      return;
    }

    viewport.scrollTo({
      top: viewport.scrollHeight - viewport.clientHeight,
      behavior: shouldReduceMotion ? 'auto' : 'smooth',
    });
  }, [refScroll, shouldReduceMotion]);

  const scrollToEnd = useCallback((): void => {
    scrollViewportToEnd();
    refFollowing.current = true;
    setStepsBelow(0);
  }, [scrollViewportToEnd]);

  useEffect(() => {
    if (directorControlled || revealedCount <= 1) {
      return;
    }

    if (refFollowing.current) {
      scrollViewportToEnd();
    } else {
      setStepsBelow((count) => count + 1);
    }
  }, [directorControlled, revealedCount, scrollViewportToEnd]);

  const patch = patches[0];

  const minimapSteps = useMemo((): IMinimapStep[] => {
    const steps = [
      { id: 'ingest', title: 'Ingesting artifacts' },
      { id: 'requirements', title: 'Extracting requirements' },
      { id: 'tests', title: 'Generating and executing tests' },
      { id: 'matrix', title: 'Building the traceability matrix' },
      { id: 'patch', title: 'Proposing a fix' },
    ].map((step, index) => ({ ...step, revealed: statusFor(index) !== 'pending' }));

    steps.push({ id: 'decision', title: 'Waiting for your decision', revealed: finished });

    if (approval?.status === 'approved' && runStatus.state === 'EVIDENCE_READY') {
      steps.push({ id: 'evidence', title: 'Evidence and artifacts', revealed: true });
    }

    return steps;
  }, [statusFor, finished, approval, runStatus.state]);

  const requirementIds = useMemo(() => matrix.map((row) => row.requirement_id), [matrix]);
  const testRows = useMemo(() => {
    return matrix.map((row) => ({
      testId: row.test_id,
      requirementId: row.requirement_id,
      failed: row.row_status !== 'passed' && row.row_status !== 'rerun_passed',
    }));
  }, [matrix]);
  const failedTestCount = useMemo(() => testRows.filter((row) => row.failed).length, [testRows]);
  const fixPaths = useMemo(() => (patch ? mapFailuresToFiles(patch.failure_ids, parsePatchFiles(patch.diff)) : {}), [patch]);
  const dataFile = demo.inputs.find((input) => input.kind === 'data')?.name;

  if (!patch) {
    return <div className="rounded-lg bg-destructive-soft p-4 text-sm text-destructive">No patch proposal found for {demo.runId}.</div>;
  }

  return (
    <div className="mx-auto w-full max-w-[880px] pb-10">
      {directorControlled && (
        <div hidden aria-hidden="true">
          <span id="director-observation-requirements">
            {requirementIds.length} schema-validated requirements: {requirementIds.join(', ')}.
          </span>
          <span id="director-observation-failures">
            {testRows.length} deterministic tests completed; {failedTestCount} failed. Tests: {testRows.map((row) => row.testId).join(', ')}.
          </span>
          <span id="director-observation-traceability">
            {matrix.length} traceability rows connect requirements, tests, failures, and patch {patch.patch_id}.
          </span>
          <span id="director-observation-patch">
            {patch.patch_id} was proposed by Codex for failures {patch.failure_ids.join(', ')} and is pending human review.
          </span>
          <span id="director-observation-approval">
            Melinda is the named reviewer and must choose Approve or Reject after reviewing the complete diff.
          </span>
        </div>
      )}
      <StepMinimap steps={minimapSteps} refScroll={refScroll} />
      <div className="mb-6">
        <div className="eyebrow flex items-center gap-1.5">
          {demo.runId}
          <Dot />
          {runStatus.mode === 'fixture' ? 'fixture replay' : 'live GPT + Codex'}
        </div>
        <h2 className="mt-1 text-[22px] font-medium tracking-display">
          {demo.title}, <span className="grad">gated by you</span>
        </h2>
      </div>

      <AgentStep
        id="step-ingest"
        title="Ingesting artifacts"
        activity="Registering the spec, source data, and target schema"
        meta="3 artifacts"
        status={statusFor(0)}
      >
        <IngestBlock demo={demo} droppedFiles={droppedFiles} />
      </AgentStep>

      <AgentStep
        id="step-requirements"
        title="Extracting requirements"
        activity={
          runStatus.mode === 'fixture'
            ? 'Replaying the frozen schema-validated control manifest'
            : 'GPT-5.6 reads the spec and emits a schema-validated control manifest'
        }
        meta={`${requirementIds.length} requirements`}
        status={statusFor(1)}
      >
        <RequirementsBlock requirementIds={requirementIds} />
      </AgentStep>

      <AgentStep
        id="step-tests"
        title="Generating and executing tests"
        activity="Deterministic migration checks execute against the canonical source records"
        meta={
          <>
            {testRows.length} tests
            <Dot />
            {failedTestCount} failed
          </>
        }
        status={statusFor(2)}
      >
        <TestsBlock rows={testRows} />
      </AgentStep>

      <AgentStep
        id="step-matrix"
        title="Building the traceability matrix"
        activity="Requirement to test to failure to patch; unfold a row for the failure evidence"
        meta={`${matrix.length} rows`}
        status={statusFor(3)}
      >
        <MatrixBlock runId={demo.runId} fixPaths={fixPaths} dataFileName={dataFile} onHoverFailure={setHoveredFailureId} />
      </AgentStep>

      <AgentStep
        id="step-patch"
        title="Proposing a fix"
        activity={
          runStatus.mode === 'fixture'
            ? 'Replaying the frozen Codex patch proposal'
            : 'Codex proposes a read-only diff; hover a fix location above to see its file light up'
        }
        meta={patch.patch_id}
        status={statusFor(4)}
      >
        <PatchBlock patch={patch} hoveredFailureId={hoveredFailureId} onHoverFailure={setHoveredFailureId} />
      </AgentStep>

      {!!approval && (
        <AgentStep id="step-decision" title="Waiting for your decision" activity="Decision recorded in the audit trail" status="done">
          <DecisionBlock runId={demo.runId} patch={patch} />
        </AgentStep>
      )}

      {/* While the gate waits it IS the final step, pinned to the
       * viewport bottom so approve/reject stays in reach wherever the
       * evidence takes the reader; the card carries its own header so
       * no in-flow step title gets ghosted underneath it. Sticky
       * needs this tall container as its parent: inside a step it
       * would have no room to travel. */}
      <AnimatePresence>
        {finished && !approval && (
          <div
            id="step-decision"
            className={cn(
              /* Solid page background behind the card so nothing shows
               * through the rounded corner notches while pinned. */
              'sticky bottom-8 z-20 bg-background pl-9',
              'before:pointer-events-none before:absolute before:inset-x-0 before:-top-20 before:h-20 before:bg-linear-to-b before:from-transparent before:to-background before:to-75% before:transition-opacity before:duration-100',
              'after:pointer-events-none after:absolute after:inset-x-0 after:top-full after:h-8 after:bg-background',
              gatePinned ? 'before:opacity-100' : 'before:opacity-0',
            )}
          >
            {/* The effect lives on an inner element: the sticky
             * wrapper itself must stay untransformed or the browser
             * would recompute its pinning against a moving box. */}
            <motion.div
              initial={shouldReduceMotion ? undefined : { opacity: 0, y: 28, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={shouldReduceMotion ? undefined : { opacity: 0, y: 10, transition: { duration: 0.18 } }}
              transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
            >
              <DecisionBlock runId={demo.runId} patch={patch} />
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {approval?.status === 'approved' && runStatus.state === 'EVIDENCE_READY' && (
        <AgentStep id="step-evidence" title="Evidence and artifacts" activity="Everything on this page, downloadable and auditable" status="done">
          <DownloadsBlock demo={demo} patch={patch} />
        </AgentStep>
      )}

      <div ref={refEnd} />

      <AnimatePresence>
        {stepsBelow > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="sticky bottom-4 z-20 flex justify-center"
          >
            <Button size="sm" variant="secondary" className="rounded-4xl border shadow-lift" onClick={scrollToEnd}>
              <ArrowDown aria-hidden="true" data-icon="inline-start" />
              {stepsBelow === 1 ? 'Next step is ready' : `${stepsBelow} steps ready`}
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export { RunTimeline };
