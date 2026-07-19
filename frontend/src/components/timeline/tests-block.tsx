import { motion, useReducedMotion } from 'motion/react';

import { IdChip } from '@/components/id-chip';
import { StatusChip } from '@/components/status-chip';
import { failureMeta } from '@/lib/failure-meta';
import { staggerContainerVariants, staggerItemVariants } from '@/lib/variants';

interface ITestRow {
  testId: string;
  requirementId: string;
  failed: boolean;
}

interface ITestsBlockProps {
  rows: ITestRow[];
}

const TestsBlock = ({ rows }: ITestsBlockProps) => {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      className="overflow-hidden rounded-lg border bg-card shadow-soft"
      variants={shouldReduceMotion ? undefined : staggerContainerVariants}
      initial={shouldReduceMotion ? undefined : 'hidden'}
      animate="visible"
    >
      {rows.map((row) => (
        <motion.div
          key={row.testId}
          data-director-target={row.failed ? 'failed-test-row' : undefined}
          variants={shouldReduceMotion ? undefined : staggerItemVariants}
          className="flex items-center gap-3 border-b px-3.5 py-2.5 last:border-b-0"
        >
          <IdChip id={row.testId} tone="test" />
          <span className="truncate text-xs">verifies {failureMeta(row.requirementId).requirementText.toLowerCase()}</span>
          <span className="ml-auto">
            <StatusChip status={row.failed ? 'failed' : 'passed'} />
          </span>
        </motion.div>
      ))}
    </motion.div>
  );
};

export { TestsBlock };
