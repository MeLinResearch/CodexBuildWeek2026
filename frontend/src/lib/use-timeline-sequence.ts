import { useCallback, useEffect, useRef, useState } from 'react';

type TStepStatus = 'pending' | 'thinking' | 'reading' | 'done';

interface IStepTiming {
  /* Header with spinner only, before results land. */
  thinkMs: number;
  /* Results visible, time to read before the next step starts. */
  readMs: number;
}

/* Sequential agent-feed reveal with two phases per step: the step
 * "thinks" (spinner, no content), then its results appear and hold
 * long enough to read, then the next step begins. Reduced motion (or
 * skip) completes everything immediately. */
const useTimelineSequence = (timings: IStepTiming[], reduced: boolean) => {
  const [position, setPosition] = useState(reduced ? timings.length * 2 : 0);
  const refTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (position >= timings.length * 2) {
      return;
    }

    const stepIndex = Math.floor(position / 2);
    const timing = timings[stepIndex];

    if (!timing) {
      return;
    }

    const delay = position % 2 === 0 ? timing.thinkMs : timing.readMs;
    refTimer.current = setTimeout(() => {
      setPosition((current) => current + 1);
    }, delay);

    return () => {
      if (refTimer.current) {
        clearTimeout(refTimer.current);
      }
    };
  }, [position, timings]);

  const skip = useCallback((): void => {
    setPosition(timings.length * 2);
  }, [timings.length]);

  const statusFor = useCallback(
    (index: number): TStepStatus => {
      const stepIndex = Math.floor(position / 2);

      if (index > stepIndex) {
        return 'pending';
      }

      if (index < stepIndex) {
        return 'done';
      }

      return position % 2 === 0 ? 'thinking' : 'reading';
    },
    [position],
  );

  const finished = position >= timings.length * 2;

  return { statusFor, skip, finished };
};

export type { IStepTiming, TStepStatus };
export { useTimelineSequence };
