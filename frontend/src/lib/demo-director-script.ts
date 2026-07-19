type TDirectorSpeaker = 'melinda' | 'codex' | 'pivanov';
type TDirectorPhase = 'intro' | 'live_wait' | 'requirements' | 'failures' | 'traceability' | 'patch' | 'approval' | 'evidence' | 'close';

interface IDirectorLine {
  speaker: TDirectorSpeaker;
  text: string;
}

interface IDirectorTurn {
  lines: IDirectorLine[];
}

const DIRECTOR_APPROVAL_NOTE = 'Reviewed the complete diff; approved for deterministic verification in the disposable workspace.';

const SPEAKER_LABELS: Record<TDirectorSpeaker, string> = {
  melinda: 'Melinda',
  codex: 'Codex · AI voice',
  pivanov: 'Pavel',
};

/* These lines are used only if live narration generation fails. They preserve
 * factual continuity without pretending that the model returned a turn. */
const FALLBACK_LINES: Record<TDirectorPhase, readonly IDirectorLine[]> = {
  intro: [
    {
      speaker: 'melinda',
      text: 'Hey everyone, welcome! I am Melinda, here with Pavel and our AI teammate Codex, and this is Release Assurance, our OpenAI Build Week project.',
    },
    {
      speaker: 'pivanov',
      text: 'Today we run a real bank migration check live: GPT five point six reads the spec, Codex proposes the fix, and a human approves.',
    },
  ],
  live_wait: [{ speaker: 'pivanov', text: 'The director is waiting for the real GPT five point six and Codex result.' }],
  requirements: [{ speaker: 'pivanov', text: 'GPT five point six extracted the explicit controls, and the manifest passed schema validation.' }],
  failures: [{ speaker: 'melinda', text: 'Deterministic checks found three blocking defects in the canonical synthetic records.' }],
  traceability: [{ speaker: 'pivanov', text: 'Each failed record maps back to its exact test and original requirement.' }],
  patch: [{ speaker: 'codex', text: 'I prepared a read-only patch proposal for human review.' }],
  approval: [{ speaker: 'pivanov', text: 'Codex proposes; a named human reviews and approves before verification.' }],
  evidence: [{ speaker: 'melinda', text: 'The approved rerun passed, and its evidence pack is ready.' }],
  close: [{ speaker: 'pivanov', text: 'Two people, one week, Codex as the third teammate.' }],
};

const isDirectorSpaceKey = (event: {
  code: string;
  repeat: boolean;
  altKey: boolean;
  ctrlKey: boolean;
  metaKey: boolean;
  shiftKey: boolean;
}): boolean => {
  return event.code === 'Space' && !event.repeat && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey;
};

const isDirectorSpeaker = (value: unknown): value is TDirectorSpeaker => {
  return value === 'melinda' || value === 'codex' || value === 'pivanov';
};

const isDirectorTurn = (value: unknown): value is IDirectorTurn => {
  if (!value || typeof value !== 'object' || !('lines' in value) || !Array.isArray(value.lines)) {
    return false;
  }

  return (
    value.lines.length > 0 &&
    value.lines.length <= 3 &&
    value.lines.every((line) => {
      return (
        !!line &&
        typeof line === 'object' &&
        'speaker' in line &&
        isDirectorSpeaker(line.speaker) &&
        'text' in line &&
        typeof line.text === 'string' &&
        line.text.trim().length > 0
      );
    })
  );
};

export type { IDirectorLine, IDirectorTurn, TDirectorPhase, TDirectorSpeaker };
export { DIRECTOR_APPROVAL_NOTE, FALLBACK_LINES, isDirectorSpaceKey, isDirectorTurn, SPEAKER_LABELS };
