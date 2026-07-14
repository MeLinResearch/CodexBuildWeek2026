import { LoaderCircle } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import type { ReactNode } from 'react';

import type { TStepStatus } from '@/lib/use-timeline-sequence';
import { cn } from '@/lib/utils';
import { fadeInUpVariants } from '@/lib/variants';

interface IAgentStepProps {
  title: string;
  activity: string;
  status: TStepStatus | 'attn';
  meta?: ReactNode;
  children?: ReactNode;
}

const AgentStep = ({ title, activity, status, meta, children }: IAgentStepProps) => {
  const shouldReduceMotion = useReducedMotion();

  if (status === 'pending') {
    return null;
  }

  const thinking = status === 'thinking';
  const showContent = !thinking && !!children;

  return (
    <motion.section
      variants={shouldReduceMotion ? undefined : fadeInUpVariants}
      initial={shouldReduceMotion ? undefined : 'hidden'}
      animate="visible"
      className="relative pb-8 pl-9 last:pb-2"
    >
      <span aria-hidden="true" className="absolute top-7 bottom-0 left-[11px] w-px bg-border" />
      <span
        aria-hidden="true"
        className={cn(
          'absolute top-0.5 left-0 flex size-[23px] items-center justify-center rounded-full border bg-card shadow-soft',
          thinking && 'border-primary/30 text-primary dark:text-primary-subtle',
          (status === 'reading' || status === 'done') && 'border-success/30 text-success',
          status === 'attn' && 'animate-attn-pulse border-warning/40 text-warning',
        )}
      >
        {thinking ? (
          <LoaderCircle aria-hidden="true" className="size-3.5 animate-spin" />
        ) : status === 'attn' ? (
          <span className="size-2 rounded-full bg-warning-indicator" />
        ) : (
          <span className="size-2 rounded-full bg-success-indicator" />
        )}
      </span>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
        <h3 className="text-[15px] font-medium tracking-display">{title}</h3>
        {!thinking && !!meta && (
          <motion.span
            initial={shouldReduceMotion ? undefined : { opacity: 0 }}
            animate={{ opacity: 1 }}
            className="inline-flex items-center gap-1.5 font-mono text-3xs text-faint-foreground"
          >
            {meta}
          </motion.span>
        )}
      </div>
      <p className={cn('mt-0.5 text-xs', thinking ? 'animate-attn-pulse text-primary dark:text-primary-subtle' : 'text-muted-foreground')}>
        {thinking ? `${activity}…` : activity}
      </p>
      {showContent && <div className="mt-3.5">{children}</div>}
    </motion.section>
  );
};

export { AgentStep };
