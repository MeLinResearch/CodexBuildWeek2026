import { useQuery, useSuspenseQuery } from '@tanstack/react-query';
import { ChevronRight, ShieldCheck } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { Fragment, useEffect, useMemo, useState } from 'react';

import { failureQuery, traceabilityMatrixQuery } from '@/api/queries';
import { Dot } from '@/components/dot';
import { IdChip } from '@/components/id-chip';
import { StatusChip } from '@/components/status-chip';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { failureMeta } from '@/lib/failure-meta';
import { cn } from '@/lib/utils';
import { staggerContainerVariants, staggerItemVariants } from '@/lib/variants';
import { useRunUi } from '@/state/run-store';

/* Highlights what the migration lost: the part of the expected value
 * that is missing from the actual one (e.g. the stripped leading
 * zeros of 00012345 vs 12345). */
const splitExpected = (expected: string, actual: string): [string, string] => {
  if (expected.endsWith(actual) && expected !== actual) {
    return [expected.slice(0, expected.length - actual.length), actual];
  }

  return ['', expected];
};

interface IFailureDetailProps {
  runId: string;
  failureId: string;
  showFailureId: boolean;
  fixPath?: string;
  dataFileName?: string;
  onHoverFailure: (failureId: string | null) => void;
}

/* The complete failed record, inline: this is the single place the
 * record renders, so nothing here duplicates another view. */
const FailureDetail = ({ runId, failureId, showFailureId, fixPath, dataFileName, onHoverFailure }: IFailureDetailProps) => {
  const failureResult = useQuery(failureQuery(runId, failureId));
  const failure = failureResult.data;

  if (!failure) {
    return <Skeleton className="h-20 w-full" />;
  }

  const meta = failureMeta(failure.requirement_id, failure);
  const [lost, kept] = splitExpected(failure.expected, failure.actual);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {showFailureId && <IdChip id={failure.failure_id} tone="fail" />}
        <span className="text-xs font-medium">{meta.title}</span>
        <StatusChip status={failure.severity} />
      </div>

      <p className="text-xs leading-relaxed text-muted-foreground">
        {meta.meaning}
        {!!fixPath && (
          <>
            {' '}
            Fixed in{' '}
            <button
              type="button"
              onClick={() => {
                document.getElementById(`diff-file-${fixPath}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                onHoverFailure(failureId);
                setTimeout(() => onHoverFailure(null), 1600);
              }}
              onMouseEnter={() => onHoverFailure(failureId)}
              onMouseLeave={() => onHoverFailure(null)}
              className="font-mono text-[11px] font-semibold text-primary underline decoration-primary/40 decoration-dotted underline-offset-4 transition-colors hover:decoration-primary dark:text-primary-subtle"
            >
              {fixPath}
            </button>
            .
          </>
        )}
      </p>

      <div className="overflow-hidden rounded-lg border bg-card shadow-soft">
        <div className="flex items-center gap-2.5 border-b bg-surface-sunken px-3 py-2">
          <span aria-hidden="true" className="flex shrink-0 gap-1.5">
            <span className="size-2.5 rounded-full bg-[#ff5f57]/80" />
            <span className="size-2.5 rounded-full bg-[#febc2e]/80" />
            <span className="size-2.5 rounded-full bg-[#28c840]/80" />
          </span>
          {!!dataFileName && <span className="min-w-0 flex-1 truncate font-mono text-4xs font-semibold text-muted-foreground">{dataFileName}</span>}
          <span className="inline-flex shrink-0 items-center gap-1.5 font-mono text-4xs whitespace-nowrap text-faint-foreground">
            {failure.record_id}
            <Dot />
            {failure.field}
          </span>
          <Tooltip>
            <TooltipTrigger
              render={
                <span className="ml-1 inline-flex shrink-0 cursor-default items-center gap-1 rounded-4xl bg-success-soft px-2 py-0.5 font-mono text-4xs font-semibold tracking-eyebrow text-success uppercase">
                  <ShieldCheck aria-hidden="true" className="size-2.5" />
                  {failure.provenance.validation_status}
                </span>
              }
            />
            <TooltipContent>
              Produced by {failure.provenance.producer === 'fixture' ? 'the frozen fixture set' : failure.provenance.producer} via{' '}
              {failure.provenance.client} in {failure.provenance.mode} mode; validated against the frozen contracts (schema{' '}
              {failure.provenance.schema_version})
            </TooltipContent>
          </Tooltip>
        </div>
        <div className="font-mono text-xs leading-relaxed">
          <div className="min-h-8 flex items-center bg-destructive-soft">
            <span className="w-8 shrink-0 text-center font-bold text-destructive">-</span>
            <span className="break-all pr-3 text-destructive">{failure.actual}</span>
          </div>
          <div className="min-h-8 flex items-center bg-success-soft">
            <span className="w-8 shrink-0 text-center font-bold text-success">+</span>
            <span className="break-all pr-3 text-success">
              {!!lost && <mark className="rounded-xs bg-success-indicator/35 px-px text-inherit">{lost}</mark>}
              {kept}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

interface IMatrixBlockProps {
  runId: string;
  fixPaths: Record<string, string>;
  dataFileName?: string;
  onHoverFailure: (failureId: string | null) => void;
}

const MatrixBlock = ({ runId, fixPaths, dataFileName, onHoverFailure }: IMatrixBlockProps) => {
  const shouldReduceMotion = useReducedMotion();
  const { data: matrix } = useSuspenseQuery(traceabilityMatrixQuery(runId));
  const { revealFailureId, revealFailure } = useRunUi();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  /* All demo runs carry a single patch, so the Patch and Approval
   * columns would repeat one value per row; they only render when
   * rows actually differ (multi-patch runs, allowed by contract). */
  const showPatchColumns = useMemo(() => {
    const patchIds = new Set(matrix.filter((row) => row.failure_ids.length > 0).map((row) => row.patch_id));
    return patchIds.size > 1;
  }, [matrix]);

  const toggle = (requirementId: string): void => {
    setExpanded((current) => ({ ...current, [requirementId]: !current[requirementId] }));
  };

  useEffect(() => {
    if (!revealFailureId) {
      return;
    }

    const row = matrix.find((candidate) => candidate.failure_ids.includes(revealFailureId));

    if (row) {
      setExpanded((current) => ({ ...current, [row.requirement_id]: true }));
      requestAnimationFrame(() => {
        document.getElementById(`matrix-row-${row.requirement_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    }

    revealFailure(null);
  }, [revealFailureId, matrix, revealFailure]);

  return (
    <motion.div
      className="overflow-hidden rounded-lg border bg-card shadow-soft"
      variants={shouldReduceMotion ? undefined : staggerContainerVariants}
      initial={shouldReduceMotion ? undefined : 'hidden'}
      animate="visible"
    >
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-full pl-4">Requirement</TableHead>
              <TableHead className="w-px">Test</TableHead>
              <TableHead className="w-px">Status</TableHead>
              <TableHead className={cn('w-px text-right', !showPatchColumns && 'pr-4')}>Failures</TableHead>
              {showPatchColumns && (
                <>
                  <TableHead className="w-px">Patch</TableHead>
                  <TableHead className="w-px pr-4">Approval</TableHead>
                </>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {matrix.map((row) => {
              const hasFailures = row.failure_ids.length > 0;
              const isOpen = hasFailures && !!expanded[row.requirement_id];
              const columnCount = showPatchColumns ? 5 : 3;

              return (
                <Fragment key={row.requirement_id}>
                  <motion.tr
                    id={`matrix-row-${row.requirement_id}`}
                    variants={shouldReduceMotion ? undefined : staggerItemVariants}
                    onClick={() => {
                      if (hasFailures) {
                        toggle(row.requirement_id);
                      }
                    }}
                    className={cn('border-b transition-colors', hasFailures && 'cursor-pointer hover:bg-muted/40')}
                  >
                    <TableCell className="py-3 pl-4">
                      <span className="flex items-start gap-2.5">
                        <span className="flex h-4 w-3.5 shrink-0 items-center">
                          {hasFailures && (
                            <ChevronRight
                              aria-hidden="true"
                              className={cn('size-3.5 text-faint-foreground transition-transform', isOpen && 'rotate-90')}
                            />
                          )}
                        </span>
                        <span>
                          <span className="block font-mono text-xs font-semibold whitespace-nowrap">{row.requirement_id}</span>
                          <span className="mt-0.5 block text-2xs whitespace-normal text-muted-foreground">
                            {failureMeta(row.requirement_id).requirementText}
                          </span>
                        </span>
                      </span>
                    </TableCell>
                    <TableCell>
                      <IdChip id={row.test_id} tone="test" />
                    </TableCell>
                    <TableCell>
                      <StatusChip status={row.row_status} />
                    </TableCell>
                    <TableCell className={cn('text-right', !showPatchColumns && 'pr-4')}>
                      <span className="inline-flex justify-end gap-1.5">
                        {row.failure_ids.map((failureId) => (
                          <IdChip key={failureId} id={failureId} tone="fail" />
                        ))}
                      </span>
                    </TableCell>
                    {showPatchColumns && (
                      <>
                        <TableCell className="font-mono text-xs font-semibold whitespace-nowrap text-primary dark:text-primary-subtle">
                          {hasFailures && row.patch_id}
                        </TableCell>
                        <TableCell className="pr-4">
                          {hasFailures && <span className="text-xs whitespace-nowrap text-faint-foreground">awaiting decision</span>}
                        </TableCell>
                      </>
                    )}
                  </motion.tr>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <tr className="border-b bg-muted/25">
                        <td colSpan={columnCount + 1} className="pr-4 pl-10">
                          <motion.div
                            initial={shouldReduceMotion ? undefined : { height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={shouldReduceMotion ? undefined : { height: 0, opacity: 0 }}
                            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
                            className="overflow-hidden"
                          >
                            <div className="space-y-4 py-3.5">
                              {row.failure_ids.map((failureId) => (
                                <FailureDetail
                                  key={failureId}
                                  runId={runId}
                                  failureId={failureId}
                                  showFailureId={row.failure_ids.length > 1}
                                  fixPath={fixPaths[failureId]}
                                  dataFileName={dataFileName}
                                  onHoverFailure={onHoverFailure}
                                />
                              ))}
                            </div>
                          </motion.div>
                        </td>
                      </tr>
                    )}
                  </AnimatePresence>
                </Fragment>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </motion.div>
  );
};

export { MatrixBlock };
