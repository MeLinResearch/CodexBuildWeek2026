import { motion, useReducedMotion } from 'motion/react';

import { IdChip } from '@/components/id-chip';
import { failureMeta } from '@/lib/failure-meta';
import { staggerContainerVariants } from '@/lib/variants';

interface IRequirementsBlockProps {
  requirementIds: string[];
}

/* Vertical list; rows fold in one by one while the container height
 * is reserved up front, so the layout under it never jumps. */
const requirementRowVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] as const },
  },
};

const RequirementsBlock = ({ requirementIds }: IRequirementsBlockProps) => {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      className="overflow-hidden rounded-lg border bg-card shadow-soft"
      variants={shouldReduceMotion ? undefined : staggerContainerVariants}
      initial={shouldReduceMotion ? undefined : 'hidden'}
      animate="visible"
    >
      {requirementIds.map((requirementId) => (
        <motion.div
          key={requirementId}
          variants={shouldReduceMotion ? undefined : requirementRowVariants}
          className="flex items-center gap-3 border-b px-3.5 py-2.5 last:border-b-0"
        >
          <IdChip id={requirementId} tone="req" />
          <span className="truncate text-xs">{failureMeta(requirementId).requirementText}</span>
        </motion.div>
      ))}
    </motion.div>
  );
};

export { RequirementsBlock };
