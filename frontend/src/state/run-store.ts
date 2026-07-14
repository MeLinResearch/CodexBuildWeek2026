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

/* The subset of contract run states the fixture replay walks through
 * (contracts/run_status.schema.json); the header chip mirrors them. */
type TReplayState = 'CREATED' | 'INGESTED' | 'MANIFEST_READY' | 'EXECUTED' | 'TRIAGED' | 'PATCH_PENDING';

interface IRunUiState {
  droppedFiles: IDroppedFile[] | null;
  approval: IApprovalRecord | null;
  /* One-shot request to unfold (and scroll to) the matrix row that
   * contains this failure; the matrix consumes and clears it. */
  revealFailureId: string | null;
  /* Where the replay currently stands; the timeline advances it as
   * each step's results land and the header chip displays it. */
  replayState: TReplayState | null;
}

interface IRunUiStore extends IRunUiState {
  /* Clears per-run state when a run starts; dropped files ride along
   * so the ingest step can show the user's own bytes. The run itself
   * lives in the URL (/$runId), which is what makes refresh work. */
  beginRun: (droppedFiles?: IDroppedFile[]) => void;
  reset: () => void;
  recordApproval: (approval: IApprovalRecord) => void;
  revealFailure: (failureId: string | null) => void;
  setReplayState: (replayState: TReplayState) => void;
}

const initialState: IRunUiState = {
  droppedFiles: null,
  approval: null,
  revealFailureId: null,
  replayState: null,
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
  setReplayState: (replayState) => {
    set({ replayState });
  },
}));

export type { IDroppedFile, TReplayState };
export { useRunUi };
