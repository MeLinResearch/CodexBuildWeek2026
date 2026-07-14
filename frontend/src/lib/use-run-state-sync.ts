import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { runStatusQuery } from '@/api/queries';

/* Companion to the polled status query: when the backend moves the
 * run to a new state, everything derived from it (matrix, failures,
 * patches) refetches, so live-mode content follows the pipeline
 * without any component wiring. Static fixture states never fire. */
const useRunStateSync = (runId: string): void => {
  const queryClient = useQueryClient();
  const statusResult = useQuery(runStatusQuery(runId));
  const state = statusResult.data?.state;
  const refPreviousState = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (state !== undefined && refPreviousState.current !== undefined && refPreviousState.current !== state) {
      queryClient.invalidateQueries({
        predicate: (query) => {
          const [scope, id, resource] = query.queryKey;
          return scope === 'runs' && id === runId && resource !== 'status';
        },
      });
    }

    refPreviousState.current = state;
  }, [state, runId, queryClient]);
};

export { useRunStateSync };
