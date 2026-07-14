import { useSuspenseQuery } from '@tanstack/react-query';
import { ArrowDown } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { patchesQuery, traceabilityMatrixQuery } from '@/api/queries';
import { Dot } from '@/components/dot';
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
import { type IStepTiming, useTimelineSequence } from '@/lib/use-timeline-sequence';
import { useRunUi } from '@/state/run-store';

/* Paced for a human watching: each step thinks with a spinner first,
 * then its results hold long enough to actually read. */
const STEP_TIMINGS: IStepTiming[] = [
  { thinkMs: 1400, readMs: 3600 },
  { thinkMs: 1600, readMs: 2600 },
  { thinkMs: 1400, readMs: 3000 },
  { thinkMs: 1800, readMs: 4800 },
  { thinkMs: 2000, readMs: 4600 },
];

const FOLLOW_THRESHOLD_PX = 140;

interface IRunTimelineProps {
  demo: IDemo;
  refScroll: React.RefObject<HTMLElement | null>;
}

const RunTimeline = ({ demo, refScroll }: IRunTimelineProps) => {
  const shouldReduceMotion = useReducedMotion();
  const { droppedFiles, approval } = useRunUi();
  const { data: matrix } = useSuspenseQuery(traceabilityMatrixQuery(demo.runId));
  const { data: patches } = useSuspenseQuery(patchesQuery(demo.runId));

  const [hoveredFailureId, setHoveredFailureId] = useState<string | null>(null);
  const { statusFor, skip, finished } = useTimelineSequence(STEP_TIMINGS, !!shouldReduceMotion);

  const refEnd = useRef<HTMLDivElement>(null);
  const refFollowing = useRef(true);
  const [stepsBelow, setStepsBelow] = useState(0);

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

  const revealedCount =
    STEP_TIMINGS.filter((_, index) => statusFor(index) === 'reading' || statusFor(index) === 'done').length + (finished ? 1 : 0) + (approval ? 1 : 0);

  const scrollToEnd = useCallback((): void => {
    refEnd.current?.scrollIntoView({ behavior: shouldReduceMotion ? 'auto' : 'smooth', block: 'end' });
    refFollowing.current = true;
    setStepsBelow(0);
  }, [shouldReduceMotion]);

  useEffect(() => {
    if (revealedCount <= 1) {
      return;
    }

    if (refFollowing.current) {
      refEnd.current?.scrollIntoView({ behavior: shouldReduceMotion ? 'auto' : 'smooth', block: 'end' });
    } else {
      setStepsBelow((count) => count + 1);
    }
  }, [revealedCount, shouldReduceMotion]);

  const patch = patches[0];
  const requirementIds = useMemo(() => matrix.map((row) => row.requirement_id), [matrix]);
  const testRows = useMemo(() => {
    return matrix.map((row) => ({ testId: row.test_id, requirementId: row.requirement_id, failed: row.failure_ids.length > 0 }));
  }, [matrix]);
  const failureIds = useMemo(() => matrix.flatMap((row) => row.failure_ids), [matrix]);
  const fixPaths = useMemo(() => (patch ? mapFailuresToFiles(patch.failure_ids, parsePatchFiles(patch.diff)) : {}), [patch]);
  const dataFile = demo.inputs.find((input) => input.kind === 'data')?.name;

  if (!patch) {
    return <div className="rounded-lg bg-destructive-soft p-4 text-sm text-destructive">No patch proposal found for {demo.runId}.</div>;
  }

  return (
    <div className="mx-auto w-full max-w-[880px] pb-10">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="eyebrow flex items-center gap-1.5">
            {demo.runId}
            <Dot />
            fixture replay
          </div>
          <h2 className="mt-1 text-[22px] font-medium tracking-display">
            {demo.title}, <span className="grad">gated by you</span>
          </h2>
        </div>
        {!finished && (
          <Button size="sm" variant="ghost" onClick={skip}>
            Skip animation
          </Button>
        )}
      </div>

      <AgentStep title="Ingesting artifacts" activity="Registering the spec, source data, and target schema" meta="3 artifacts" status={statusFor(0)}>
        <IngestBlock demo={demo} droppedFiles={droppedFiles} />
      </AgentStep>

      <AgentStep
        title="Extracting requirements"
        activity="GPT-5.6 reads the spec and emits a schema-validated control manifest"
        meta={`${requirementIds.length} requirements`}
        status={statusFor(1)}
      >
        <RequirementsBlock requirementIds={requirementIds} />
      </AgentStep>

      <AgentStep
        title="Generating and executing tests"
        activity="Codex writes one migration test per requirement and runs them against the migrated records"
        meta={
          <>
            {testRows.length} tests
            <Dot />
            {failureIds.length} failed
          </>
        }
        status={statusFor(2)}
      >
        <TestsBlock rows={testRows} />
      </AgentStep>

      <AgentStep
        title="Building the traceability matrix"
        activity="Requirement to test to failure to patch; unfold a row for the failure evidence"
        meta={`${matrix.length} rows`}
        status={statusFor(3)}
      >
        <MatrixBlock runId={demo.runId} fixPaths={fixPaths} dataFileName={dataFile} onHoverFailure={setHoveredFailureId} />
      </AgentStep>

      <AgentStep
        title="Proposing a fix"
        activity="Codex proposes a diff; hover a fix location above to see its file light up"
        meta={patch.patch_id}
        status={statusFor(4)}
      >
        <PatchBlock patch={patch} hoveredFailureId={hoveredFailureId} onHoverFailure={setHoveredFailureId} />
      </AgentStep>

      <AgentStep
        title="Waiting for your decision"
        activity={approval ? 'Decision recorded in the audit trail' : 'The gate is human: nothing is applied without approval'}
        status={finished ? (approval ? 'done' : 'attn') : 'pending'}
      >
        <DecisionBlock runId={demo.runId} patch={patch} />
      </AgentStep>

      {!!approval && (
        <AgentStep title="Evidence and artifacts" activity="Everything on this page, downloadable and auditable" status="done">
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
            className="sticky bottom-4 flex justify-center"
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
