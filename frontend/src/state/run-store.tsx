import { createContext, type ReactNode, useCallback, useContext, useMemo, useReducer } from 'react';

interface IApprovalRecord {
  status: 'approved' | 'rejected';
  actor: string;
  note: string | null;
}

interface IDroppedFile {
  name: string;
  content: string;
}

interface IRunUiState {
  demoId: string | null;
  droppedFiles: IDroppedFile[] | null;
  approval: IApprovalRecord | null;
  /* One-shot request to unfold (and scroll to) the matrix row that
   * contains this failure; the matrix consumes and clears it. */
  revealFailureId: string | null;
}

type TRunUiAction =
  | { type: 'select-demo'; demoId: string; droppedFiles: IDroppedFile[] | null }
  | { type: 'reset' }
  | { type: 'approval'; approval: IApprovalRecord }
  | { type: 'reveal-failure'; failureId: string | null };

const initialState: IRunUiState = {
  demoId: null,
  droppedFiles: null,
  approval: null,
  revealFailureId: null,
};

const reducer = (state: IRunUiState, action: TRunUiAction): IRunUiState => {
  switch (action.type) {
    case 'select-demo': {
      return { ...initialState, demoId: action.demoId, droppedFiles: action.droppedFiles };
    }
    case 'reset': {
      return initialState;
    }
    case 'approval': {
      return { ...state, approval: action.approval };
    }
    case 'reveal-failure': {
      return { ...state, revealFailureId: action.failureId };
    }
    default: {
      return state;
    }
  }
};

interface IRunUiStore extends IRunUiState {
  selectDemo: (demoId: string, droppedFiles?: IDroppedFile[]) => void;
  reset: () => void;
  recordApproval: (approval: IApprovalRecord) => void;
  revealFailure: (failureId: string | null) => void;
}

const RunUiContext = createContext<IRunUiStore | null>(null);

const RunUiProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(reducer, initialState);

  const selectDemo = useCallback((demoId: string, droppedFiles?: IDroppedFile[]): void => {
    dispatch({ type: 'select-demo', demoId, droppedFiles: droppedFiles ?? null });
  }, []);

  const reset = useCallback((): void => {
    dispatch({ type: 'reset' });
  }, []);

  const recordApproval = useCallback((approval: IApprovalRecord): void => {
    dispatch({ type: 'approval', approval });
  }, []);

  const revealFailure = useCallback((failureId: string | null): void => {
    dispatch({ type: 'reveal-failure', failureId });
  }, []);

  const store = useMemo<IRunUiStore>(() => {
    return { ...state, selectDemo, reset, recordApproval, revealFailure };
  }, [state, selectDemo, reset, recordApproval, revealFailure]);

  return <RunUiContext.Provider value={store}>{children}</RunUiContext.Provider>;
};

const useRunUi = (): IRunUiStore => {
  const store = useContext(RunUiContext);

  if (!store) {
    throw new Error('useRunUi must be used inside RunUiProvider');
  }

  return store;
};

export type { IDroppedFile };
export { RunUiProvider, useRunUi };
