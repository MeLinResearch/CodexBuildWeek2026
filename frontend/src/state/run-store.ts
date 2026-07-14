import { create } from 'zustand';

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
  droppedFiles: IDroppedFile[] | null;
  approval: IApprovalRecord | null;
  /* One-shot request to unfold (and scroll to) the matrix row that
   * contains this failure; the matrix consumes and clears it. */
  revealFailureId: string | null;
}

interface IRunUiStore extends IRunUiState {
  /* Clears per-run state when a run starts; dropped files ride along
   * so the ingest step can show the user's own bytes. The run itself
   * lives in the URL (/$runId), which is what makes refresh work. */
  beginRun: (droppedFiles?: IDroppedFile[]) => void;
  reset: () => void;
  recordApproval: (approval: IApprovalRecord) => void;
  revealFailure: (failureId: string | null) => void;
}

const initialState: IRunUiState = {
  droppedFiles: null,
  approval: null,
  revealFailureId: null,
};

const useRunUi = create<IRunUiStore>((set) => ({
  ...initialState,
  beginRun: (droppedFiles) => {
    set({ ...initialState, droppedFiles: droppedFiles ?? null });
  },
  reset: () => {
    set(initialState);
  },
  recordApproval: (approval) => {
    set({ approval });
  },
  revealFailure: (failureId) => {
    set({ revealFailureId: failureId });
  },
}));

export type { IDroppedFile };
export { useRunUi };
