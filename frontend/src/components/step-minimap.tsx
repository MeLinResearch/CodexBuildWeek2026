import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useEffect, useState } from 'react';

import { cn } from '@/lib/utils';

interface IMinimapStep {
  id: string;
  title: string;
  revealed: boolean;
}

interface IStepMinimapProps {
  steps: IMinimapStep[];
  refScroll: React.RefObject<HTMLElement | null>;
}

/* A ChatGPT-style tick rail pinned to the left edge: one dash per
 * pipeline step, filling in as the replay reveals them. Hovering
 * names a step, clicking scrolls to it. */
const StepMinimap = ({ steps, refScroll }: IStepMinimapProps) => {
  const shouldReduceMotion = useReducedMotion();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  /* Reference-line scrollspy: the active step is the last one whose
   * top sits above 35% of the viewport. Intersection ratios would
   * bias against tall sections and misfire on the sticky gate card,
   * which is always fully visible while pinned. At the very bottom
   * the last revealed step wins regardless. */
  useEffect(() => {
    const root = refScroll.current;

    if (!root) {
      return;
    }

    let frame = 0;

    const update = (): void => {
      frame = 0;
      const rootRect = root.getBoundingClientRect();
      const referenceLine = rootRect.top + rootRect.height * 0.35;
      let current: string | null = null;

      for (const step of steps) {
        if (!step.revealed) {
          continue;
        }

        const section = document.getElementById(`step-${step.id}`);

        if (section && section.getBoundingClientRect().top <= referenceLine) {
          current = step.id;
        }
      }

      /* The timeline carries ~64px of trailing padding, so "at the
       * bottom" must tolerate it or the snap never fires. */
      if (root.scrollTop + root.clientHeight >= root.scrollHeight - 80) {
        const last = [...steps].reverse().find((step) => step.revealed);
        current = last?.id ?? current;
      }

      if (current) {
        setActiveId(current);
      }
    };

    const handleScroll = (): void => {
      if (!frame) {
        frame = requestAnimationFrame(update);
      }
    };

    update();
    root.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      root.removeEventListener('scroll', handleScroll);

      if (frame) {
        cancelAnimationFrame(frame);
      }
    };
  }, [steps, refScroll]);

  return (
    <nav aria-label="Pipeline steps" className="fixed top-1/2 left-3 z-20 hidden -translate-y-1/2 flex-col md:flex">
      {steps.map((step, index) => {
        const isActive = activeId === step.id;
        /* The rail is one indigo gradient anchored on the active
         * tick: full color where you are, fading toward 30% with
         * distance, so the bright point travels as you scroll. */
        const activeIndex = steps.findIndex((candidate) => candidate.id === activeId);
        const distance = activeIndex >= 0 ? Math.abs(index - activeIndex) : index;
        const alpha = Math.max(1 - distance * 0.2, 0.3);

        return (
          <button
            key={step.id}
            type="button"
            disabled={!step.revealed}
            aria-label={step.title}
            onMouseEnter={() => setHoveredId(step.id)}
            onMouseLeave={() => setHoveredId(null)}
            onClick={() => {
              document.getElementById(`step-${step.id}`)?.scrollIntoView({ behavior: shouldReduceMotion ? 'auto' : 'smooth', block: 'start' });
            }}
            className="group/tick relative flex items-center py-1.5 pr-8"
          >
            <AnimatePresence>
              {hoveredId === step.id && step.revealed && (
                <motion.span
                  initial={shouldReduceMotion ? undefined : { opacity: 0, x: -6, scale: 0.96 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={shouldReduceMotion ? undefined : { opacity: 0, x: -6, scale: 0.96 }}
                  transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
                  className="absolute left-7 rounded-md border bg-popover px-2.5 py-1 text-2xs font-medium whitespace-nowrap text-popover-foreground shadow-lift"
                >
                  {step.title}
                </motion.span>
              )}
            </AnimatePresence>
            <span
              style={{ backgroundColor: 'var(--primary)', opacity: step.revealed ? (hoveredId === step.id ? 1 : alpha) : 0.15 }}
              className={cn(
                'h-0.5 rounded-full transition-all duration-200',
                step.revealed ? 'w-4 group-hover/tick:w-6' : 'w-2.5',
                isActive && step.revealed && 'w-6',
              )}
            />
          </button>
        );
      })}
    </nav>
  );
};

export type { IMinimapStep };
export { StepMinimap };
