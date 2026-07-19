type TDirectorSpeaker = 'melinda' | 'codex' | 'pivanov';
type TDirectorPhase = 'intro' | 'live_wait' | 'requirements' | 'failures' | 'traceability' | 'patch' | 'review' | 'approval' | 'evidence' | 'close';
type TDirectorDelivery =
  | 'default'
  | 'intro_banter_question'
  | 'intro_on_air_pivot'
  | 'intro_reset'
  | 'intro_host_welcome'
  | 'intro_launch'
  | 'intro_codex_welcome'
  | 'intro_run_start'
  | 'intro_codex_on_it'
  | 'review_request'
  | 'review_codex_tease'
  | 'review_melinda_reply'
  | 'approval_decision'
  | 'approval_note'
  | 'verify_nervous'
  | 'close_thanks'
  | 'close_signoff'
  | 'wait_banter'
  | 'reveal_requirements'
  | 'reveal_failures'
  | 'reveal_traceability'
  | 'patch_present'
  | 'reveal_evidence';

interface IDirectorLine {
  speaker: TDirectorSpeaker;
  text: string;
  delivery?: TDirectorDelivery;
}

interface IDirectorTurn {
  lines: IDirectorLine[];
}

const DIRECTOR_APPROVAL_NOTE = 'Reviewed the complete diff; approved for deterministic verification in the disposable workspace.';

const INTRO_LINES: readonly IDirectorLine[] = [
  {
    speaker: 'pivanov',
    text: 'Hmm... wait... the migration said success, but the balance was wrong?',
    delivery: 'intro_banter_question',
  },
  {
    speaker: 'melinda',
    text: 'Exactly... and nobody knew.',
    delivery: 'intro_on_air_pivot',
  },
  {
    speaker: 'melinda',
    text: 'Oops... we’re live!',
    delivery: 'intro_on_air_pivot',
  },
  {
    speaker: 'melinda',
    text: 'All right... let’s do it!',
    delivery: 'intro_reset',
  },
  {
    speaker: 'pivanov',
    text: 'Hey, everyone! I’m Pavel.',
    delivery: 'intro_host_welcome',
  },
  {
    speaker: 'melinda',
    text: 'Hi... I’m Melinda. This is Release Assurance, our OpenAI Build Week project for catching silent migration defects.',
    delivery: 'intro_host_welcome',
  },
  {
    speaker: 'melinda',
    text: 'Let’s get the live pipeline running, right?',
    delivery: 'intro_run_start',
  },
  {
    speaker: 'codex',
    text: 'Codex here... third teammate. I’ll inspect failures and propose the patch.',
    delivery: 'intro_launch',
  },
  {
    speaker: 'codex',
    text: 'On it... let’s see what the migration is hiding.',
    delivery: 'intro_codex_on_it',
  },
  {
    speaker: 'melinda',
    text: 'Nice to have you on board, Codex.',
    delivery: 'intro_codex_welcome',
  },
];

/* The verification wait and the close are scripted beats: the last
 * impression of the recording should never gamble on generation. */
const VERIFY_WAIT_LINE: IDirectorLine = {
  speaker: 'codex',
  text: 'And now my patch gets verified... this is the part where I get nervous.',
  delivery: 'verify_nervous',
};

const CLOSE_LINES: readonly IDirectorLine[] = [
  {
    speaker: 'melinda',
    text: 'That\u2019s Release Assurance... two people, one week, and Codex as the third teammate. Thanks for watching our Build Week submission!',
    delivery: 'close_thanks',
  },
  {
    speaker: 'codex',
    text: 'Codex, signing off. The evidence pack has the receipts.',
    delivery: 'close_signoff',
  },
];

const SPEAKER_LABELS: Record<TDirectorSpeaker, string> = {
  melinda: 'Melinda',
  codex: 'Codex · AI voice',
  pivanov: 'Pavel',
};

/* The intro is deliberately authored for a stable cold open. The remaining
 * lines are concise fallbacks used only if live narration generation fails. */
const FALLBACK_LINES: Record<TDirectorPhase, readonly IDirectorLine[]> = {
  intro: INTRO_LINES,
  live_wait: [{ speaker: 'pivanov', text: 'The director is waiting for the real GPT five point six and Codex result.' }],
  requirements: [{ speaker: 'pivanov', text: 'GPT five point six extracted the explicit controls, and the manifest passed schema validation.' }],
  failures: [
    { speaker: 'melinda', text: 'Deterministic checks found three blocking defects in the canonical synthetic records.' },
    { speaker: 'pivanov', text: 'And this failed record is exactly the kind of change nobody catches by eye.' },
  ],
  traceability: [
    { speaker: 'pivanov', text: 'Each failed record maps back to its exact test and original requirement.' },
    { speaker: 'codex', text: 'I kept that reasoning chain intact, from requirement through failure to candidate fix.' },
  ],
  patch: [{ speaker: 'codex', text: 'I prepared a read-only patch proposal for human review.' }],
  review: [
    {
      speaker: 'pivanov',
      text: 'Melinda, can you check the complete diff before we continue?',
      delivery: 'review_request',
    },
    {
      speaker: 'codex',
      text: 'I’m still here, Melinda... I told you it works!',
      delivery: 'review_codex_tease',
    },
    {
      speaker: 'melinda',
      text: 'Nice try, Codex... but I’ll double-check it.',
      delivery: 'review_melinda_reply',
    },
  ],
  approval: [
    {
      speaker: 'melinda',
      text: 'I’ve double-checked the complete diff. The patch looks good... so I’ll approve it.',
      delivery: 'approval_decision',
    },
    {
      speaker: 'melinda',
      text: 'I’ll add a clear review note now, so the decision is recorded.',
      delivery: 'approval_note',
    },
  ],
  evidence: [
    { speaker: 'melinda', text: 'The approved rerun passed, and its evidence pack is ready.' },
    { speaker: 'codex', text: 'My proposed change passed verification, with its diff, decision, and provenance recorded.' },
  ],
  close: CLOSE_LINES,
};

const constrainDirectorTurn = (phase: TDirectorPhase, turn: IDirectorTurn): IDirectorTurn => {
  if (phase !== 'review') {
    return turn;
  }

  return {
    lines: FALLBACK_LINES.review.map((line) => ({ ...line })),
  };
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
export {
  CLOSE_LINES,
  constrainDirectorTurn,
  DIRECTOR_APPROVAL_NOTE,
  FALLBACK_LINES,
  INTRO_LINES,
  isDirectorSpaceKey,
  isDirectorTurn,
  SPEAKER_LABELS,
  VERIFY_WAIT_LINE,
};
