import { DemoDirectorOverlay, delay, type IPreparedSpeech } from '@/lib/demo-director-overlay';
import {
  DIRECTOR_APPROVAL_NOTE,
  FALLBACK_LINES,
  type IDirectorLine,
  type IDirectorTurn,
  isDirectorSpaceKey,
  isDirectorTurn,
  type TDirectorPhase,
} from '@/lib/demo-director-script';

const LIVE_RESULT_BUDGET_MS = 90_000;
const RECORDING_BUDGET_MS = 175_000;
const STEP_TIMEOUT_MS = 45_000;

type TDirectorState = 'idle' | 'running' | 'awaiting-approval' | 'complete' | 'failed';

interface IPhasePlaybackHooks {
  before?: () => Promise<void>;
  onFirstPlaybackStarted?: () => void | Promise<void>;
}

/* A line whose audio failed to synthesize still plays as a timed
 * caption; one bad synthesis must never stop a recording. */
interface IPreparedLine {
  line: IDirectorLine;
  speech: IPreparedSpeech | null;
}

declare global {
  interface Window {
    __releaseAssuranceDemoDirectorInstalled?: boolean;
  }
}

const isEditableTarget = (target: EventTarget | null): boolean => {
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    (target instanceof HTMLElement && target.isContentEditable)
  );
};

const isVisible = (element: HTMLElement): boolean => {
  const bounds = element.getBoundingClientRect();
  const style = window.getComputedStyle(element);
  return bounds.width > 0 && bounds.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
};

const normalizedText = (element: Element): string => {
  return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
};

const observedText = (element: Element, maximumCharacters = 900): string => {
  return normalizedText(element).slice(0, maximumCharacters);
};

const findVisibleButton = (label: string | RegExp, root: ParentNode = document): HTMLButtonElement | null => {
  for (const button of root.querySelectorAll<HTMLButtonElement>('button')) {
    const text = normalizedText(button);
    const matches = typeof label === 'string' ? text === label : label.test(text);

    if (matches && isVisible(button)) {
      return button;
    }
  }

  return null;
};

const waitForValue = async <T>(read: () => T | null | undefined | false, timeoutMs: number, timeoutMessage: string): Promise<T> => {
  const startedAt = performance.now();

  while (performance.now() - startedAt < timeoutMs) {
    const value = read();

    if (value) {
      return value;
    }

    await delay(120);
  }

  throw new Error(timeoutMessage);
};

const scrollToElement = async (element: HTMLElement, block: ScrollLogicalPosition = 'center'): Promise<void> => {
  element.scrollIntoView({ behavior: 'smooth', block });
  await delay(720);
};

const waitForStep = async (id: string, ready: (step: HTMLElement) => boolean): Promise<HTMLElement> => {
  return waitForValue(
    () => {
      const step = document.getElementById(id);
      return step && ready(step) ? step : null;
    },
    STEP_TIMEOUT_MS,
    `The ${id} stage did not become ready`,
  );
};

const setTextareaValue = (textarea: HTMLTextAreaElement, value: string): void => {
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;

  if (!setter) {
    throw new Error('The approval note field cannot be controlled');
  }

  setter.call(textarea, value);
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
};

class DemoDirector {
  private state: TDirectorState = 'idle';
  private overlay: DemoDirectorOverlay | null = null;
  private approvalResolver: (() => void) | null = null;
  private liveDeadline = 0;
  private recordingStartedAt = 0;
  private aborted = false;
  private readonly history: string[] = [];

  /* Two serial chains keep the narration honest AND gapless: turn
   * generation and speech synthesis run one phase ahead on the
   * generation chain (so history order stays correct), while the
   * playback chain speaks each phase in order. The synthesis
   * round-trips happen during the previous phase's audio instead of
   * as on-screen silence. */
  private generationTail: Promise<unknown> = Promise.resolve();
  private playbackTail: Promise<void> = Promise.resolve();

  install(): void {
    window.addEventListener('keydown', this.handleKeyDown, { capture: true });
  }

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
    if (!isDirectorSpaceKey(event) || isEditableTarget(event.target)) {
      return;
    }

    if (this.state === 'awaiting-approval' && this.approvalResolver) {
      event.preventDefault();
      this.approvalResolver();
      this.approvalResolver = null;
      this.state = 'running';
      return;
    }

    if (this.state === 'running') {
      event.preventDefault();
      return;
    }

    if (this.state !== 'idle' || window.location.pathname !== '/') {
      return;
    }

    const liveButton = findVisibleButton('Run Live GPT + Codex');

    if (!liveButton) {
      return;
    }

    event.preventDefault();
    (document.activeElement as HTMLElement | null)?.blur();
    this.state = 'running';
    this.recordingStartedAt = performance.now();
    this.overlay = new DemoDirectorOverlay();
    void this.run(liveButton);
  };

  private async run(liveButton: HTMLButtonElement): Promise<void> {
    if (!this.overlay) {
      return;
    }

    try {
      const intro = await this.requestTurn(
        'intro',
        [
          'The recording just started; open like a podcast episode with greetings and introductions.',
          'This is the OpenAI Build Week submission recording.',
          'The Release Assurance start page is ready and the Run Live GPT plus Codex button is available.',
          'No run has started yet.',
        ],
        3,
      );
      await this.speakTurn(intro, async () => {
        await delay(1_400);
        await this.overlay?.moveCursorTo(liveButton, true);
        this.liveDeadline = performance.now() + LIVE_RESULT_BUDGET_MS;
      });

      if (!this.timelineIsReady()) {
        const waitingTurn = await this.requestTurn(
          'live_wait',
          ['The live button was clicked.', 'The browser still shows the live run as pending.', 'No timeline result is visible yet.'],
          2,
        );
        await this.speakTurn(waitingTurn);
      }

      /* A live run spends thirty to ninety seconds inside one POST;
       * the director keeps narrating honestly through the whole wait
       * instead of leaving dead air after two lines. */
      while (!this.timelineIsReady() && performance.now() < this.liveDeadline) {
        const elapsedSeconds = Math.max(0, Math.round((performance.now() - this.liveDeadline + LIVE_RESULT_BUDGET_MS) / 1_000));
        const followUpTurn = await this.requestTurn(
          'live_wait',
          [
            `About ${elapsedSeconds} seconds have passed since the live button was clicked.`,
            'The live run is still pending and the progress panel with the elapsed timer is visible.',
            'The director must not invent model progress.',
          ],
          1,
        );

        if (this.timelineIsReady()) {
          break;
        }

        await this.speakTurn(followUpTurn);

        if (!this.timelineIsReady()) {
          await delay(1_100);
        }
      }

      await this.waitForLiveTimeline();
      await this.presentTimeline();
      this.state = 'complete';
      this.overlay.setStatus('Walkthrough complete');
      this.overlay.stopAudio();
      this.overlay.hideCursor();
    } catch (error) {
      this.state = 'failed';
      this.aborted = true;
      const message = error instanceof Error ? error.message : 'The live walkthrough stopped unexpectedly';
      this.overlay.setCaption('codex', message, false);
      this.overlay.setStatus('Director stopped', 'error');
      this.overlay.stopAudio();
      this.overlay.hideCursor();
    }
  }

  private async presentTimeline(): Promise<void> {
    const overlay = this.overlay;

    if (!overlay) {
      return;
    }

    const requirementsStep = waitForStep('step-requirements', (step) => /REQ-\d{3}/.test(normalizedText(step)));
    const requirementsPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'requirements',
        async () => [observedText(await requirementsStep), 'The live control manifest is visible and schema validated.'],
        1,
      ),
      { before: async () => scrollToElement(await requirementsStep) },
    );

    const testsStep = waitForStep('step-tests', (step) => /TEST-\d{3}/.test(normalizedText(step)) && /failed/i.test(normalizedText(step)));
    const failuresPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'failures',
        async () => [observedText(await testsStep), 'The deterministic checks have completed and blocking failures are visible.'],
        1,
      ),
      { before: async () => scrollToElement(await testsStep) },
    );

    const matrixStep = waitForStep('step-matrix', (step) => step.querySelector('table') !== null);
    const firstFailedRow = matrixStep.then((step) => {
      return waitForValue(
        () => step.querySelector<HTMLElement>('tbody tr[id^="matrix-row-"]'),
        STEP_TIMEOUT_MS,
        'No failed traceability row became available',
      );
    });
    const traceabilityPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'traceability',
        async () => [observedText(await matrixStep), `The first expandable failed row contains: ${observedText(await firstFailedRow, 400)}`],
        1,
      ),
      {
        before: async () => scrollToElement(await matrixStep),
        onFirstPlaybackStarted: async () => {
          await delay(1_350);
          await overlay.moveCursorTo(await firstFailedRow, true);
        },
      },
    );

    const patchStep = waitForStep('step-patch', (step) => /proposed by Codex/i.test(normalizedText(step)));
    const patchPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'patch',
        async () => [
          observedText(await patchStep),
          'A complete read-only diff is visible for human review.',
          'On screen the cursor follows the fix link from the failed record straight into the diff, then demonstrates the stacked and split diff views.',
        ],
        1,
      ),
      {
        /* The UI's own guided jump: clicking the fix link inside the
         * expanded failure scrolls to the exact diff file and flashes
         * its failure chips, which beats a plain scroll. */
        before: async () => {
          const fixLink = findVisibleButton(/^reconcile\//);

          if (fixLink) {
            await overlay.moveCursorTo(fixLink, true);
            await delay(800);
            return;
          }

          await scrollToElement(await patchStep);
        },
        /* While Codex talks, show off the diff views. */
        onFirstPlaybackStarted: async () => {
          await delay(1_300);
          const splitButton = findVisibleButton('Split');

          if (!splitButton) {
            return;
          }

          await overlay.moveCursorTo(splitButton, true);
          await delay(1_800);
          const stackedButton = findVisibleButton('Stacked');

          if (stackedButton) {
            await overlay.moveCursorTo(stackedButton, true);
          }
        },
      },
    );

    const approvalButton = patchStep.then(() => {
      return waitForValue(() => findVisibleButton('Approve patch'), STEP_TIMEOUT_MS, 'The human approval gate did not become ready');
    });
    const approvalPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'approval',
        async () => {
          const button = await approvalButton;
          return [observedText(document.getElementById('step-decision') ?? button), 'The approval action requires a human Space press.'];
        },
        1,
      ),
      {
        before: async () => {
          const button = await approvalButton;
          await scrollToElement(button, 'end');
          await overlay.moveCursorTo(button);
        },
      },
    );

    await Promise.all([requirementsPlayed, failuresPlayed, traceabilityPlayed, patchPlayed, approvalPlayed]);

    await this.waitForHumanApproval();
    await this.recordApproval(await approvalButton);

    const evidenceStep = await waitForValue(
      () => {
        if (this.approvalFailed()) {
          throw new Error('The approval or rerun endpoint did not complete');
        }

        return document.getElementById('step-evidence');
      },
      60_000,
      'The approved rerun did not produce evidence',
    );
    const evidencePlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'evidence',
        async () => [
          observedText(evidenceStep),
          'The approved deterministic rerun passed in a disposable workspace.',
          'The verified suite contains 168 backend tests and 27 frontend tests.',
        ],
        2,
      ),
      { before: async () => scrollToElement(evidenceStep, 'center') },
    );

    /* The close generates while the evidence narration plays. */
    const closePlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'close',
        async () => [
          'The evidence pack is available.',
          'Codex helped build the repository and the event-driven director.',
          'The close must be brief because the recording is ending.',
        ],
        2,
      ),
      {
        before: async () => {
          const evidenceButton = findVisibleButton('Evidence pack');

          if (evidenceButton) {
            await overlay.moveCursorTo(evidenceButton);
          }

          overlay.setStatus('168 backend · 27 frontend');
        },
      },
    );

    await evidencePlayed;
    await closePlayed;
  }

  /* Chains a turn request plus per-line synthesis onto the generation
   * tail; resolves with playable audio (or caption fallbacks) for the
   * whole phase. */
  private queuePhaseGeneration(phase: TDirectorPhase, observe: () => Promise<string[]>, maxLines: number): Promise<IPreparedLine[]> {
    const generation = this.generationTail.then(async () => {
      const observations = await observe();
      const turn = await this.requestTurn(phase, observations, maxLines);

      for (const line of turn.lines) {
        this.pushHistory(line);
      }

      const overlay = this.overlay;

      if (!overlay) {
        return [];
      }

      return Promise.all(turn.lines.map((line) => this.prepareLine(line)));
    });
    this.generationTail = generation.then(
      () => undefined,
      () => undefined,
    );
    return generation;
  }

  private async prepareLine(line: IDirectorLine): Promise<IPreparedLine> {
    const overlay = this.overlay;

    if (!overlay) {
      return { line, speech: null };
    }

    try {
      return { line, speech: await overlay.prepareSpeech(line) };
    } catch {
      return { line, speech: null };
    }
  }

  private async playLine(item: IPreparedLine, onPlaybackStarted?: () => void | Promise<void>): Promise<void> {
    const overlay = this.overlay;

    if (!overlay) {
      return;
    }

    if (item.speech) {
      await overlay.playPrepared(item.speech, onPlaybackStarted);
      return;
    }

    await overlay.showCaptionOnly(item.line, onPlaybackStarted);
  }

  /* Chains playback of a prepared phase onto the playback tail; the
   * before hook keeps scrolls and cursor moves in lockstep with the
   * audio they narrate. */
  private queuePhasePlayback(preparedPromise: Promise<IPreparedLine[]>, hooks?: IPhasePlaybackHooks): Promise<void> {
    const playback = this.playbackTail.then(async () => {
      const prepared = await preparedPromise;

      if (this.aborted) {
        for (const item of prepared) {
          if (item.speech) {
            URL.revokeObjectURL(item.speech.objectUrl);
          }
        }

        return;
      }

      await hooks?.before?.();

      for (const [index, item] of prepared.entries()) {
        if (this.aborted) {
          if (item.speech) {
            URL.revokeObjectURL(item.speech.objectUrl);
          }

          continue;
        }

        await this.playLine(item, index === 0 ? hooks?.onFirstPlaybackStarted : undefined);
      }
    });
    this.playbackTail = playback.then(
      () => undefined,
      () => undefined,
    );
    return playback;
  }

  private async speakTurn(turn: IDirectorTurn, onFirstPlaybackStarted?: () => void | Promise<void>): Promise<void> {
    if (!this.overlay) {
      return;
    }

    for (const line of turn.lines) {
      this.pushHistory(line);
    }

    /* All lines synthesize in parallel; playback stays sequential. */
    const prepared = turn.lines.map((line) => this.prepareLine(line));

    for (const [index, item] of prepared.entries()) {
      await this.playLine(await item, index === 0 ? onFirstPlaybackStarted : undefined);
    }
  }

  private pushHistory(line: IDirectorLine): void {
    this.history.push(`${line.speaker}: ${line.text}`);

    if (this.history.length > 12) {
      this.history.shift();
    }
  }

  private async recordApproval(approvalButton: HTMLButtonElement): Promise<void> {
    if (!this.overlay) {
      return;
    }

    this.overlay.setStatus('Recording approval', 'attention');
    await this.overlay.moveCursorTo(approvalButton, true);

    const dialog = await waitForValue(
      () => document.querySelector<HTMLElement>('[data-slot="dialog-content"]'),
      5_000,
      'The approval dialog did not open',
    );
    const textarea = await waitForValue(() => dialog.querySelector<HTMLTextAreaElement>('textarea'), 2_000, 'The approval note field is missing');
    await this.overlay.moveCursorTo(textarea, true);

    for (let index = 1; index <= DIRECTOR_APPROVAL_NOTE.length; index += 1) {
      setTextareaValue(textarea, DIRECTOR_APPROVAL_NOTE.slice(0, index));
      await delay(13);
    }

    const confirmButton = await waitForValue(
      () => {
        const button = findVisibleButton('Approve patch', dialog);
        return button && !button.disabled ? button : null;
      },
      3_000,
      'The approval confirmation did not become available',
    );
    await this.overlay.moveCursorTo(confirmButton, true);
    this.overlay.setStatus('Verifying patch');
  }

  private waitForHumanApproval(): Promise<void> {
    if (!this.overlay) {
      return Promise.resolve();
    }

    this.state = 'awaiting-approval';
    this.overlay.setCaption('pivanov', 'Human checkpoint: press Space to record approval and run deterministic verification.', false);
    this.overlay.setStatus('Space to approve', 'attention');

    return new Promise((resolve) => {
      this.approvalResolver = resolve;
    });
  }

  private async waitForLiveTimeline(): Promise<void> {
    if (!this.overlay) {
      return;
    }

    this.overlay.setStatus('Waiting for live result', 'attention');
    const remainingBudget = Math.max(1, this.liveDeadline - performance.now());
    await waitForValue(
      () => {
        if (this.liveRunFailed()) {
          throw new Error('The live GPT plus Codex request failed; reload the page and rehearse again');
        }

        return document.getElementById('step-ingest');
      },
      remainingBudget,
      'The live run exceeded the ninety-second recording budget; reload and try again',
    );
    this.overlay.setStatus('Live result ready');
  }

  private async requestTurn(phase: TDirectorPhase, observations: string[], maxLines: number): Promise<IDirectorTurn> {
    try {
      const response = await fetch('/api/director/turn', {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phase,
          observations,
          history: this.history.slice(-12),
          remaining_seconds: this.remainingSeconds(),
          max_lines: maxLines,
        }),
      });

      if (!response.ok) {
        throw new Error(`Director turn failed with HTTP ${response.status}`);
      }

      const payload: unknown = await response.json();
      if (!isDirectorTurn(payload)) {
        throw new Error('Director turn did not match the browser contract');
      }
      return payload;
    } catch {
      return { lines: [...FALLBACK_LINES[phase]].slice(0, maxLines) };
    }
  }

  private remainingSeconds(): number {
    const elapsed = performance.now() - this.recordingStartedAt;
    return Math.max(10, Math.min(180, Math.floor((RECORDING_BUDGET_MS - elapsed) / 1_000)));
  }

  private timelineIsReady(): boolean {
    return document.getElementById('step-ingest') !== null;
  }

  private liveRunFailed(): boolean {
    return document.body.textContent?.includes('The FastAPI demo runtime did not start the run') ?? false;
  }

  private approvalFailed(): boolean {
    return document.body.textContent?.includes('The decision endpoint did not respond') ?? false;
  }
}

const installDemoDirector = (): void => {
  if (window.__releaseAssuranceDemoDirectorInstalled) {
    return;
  }

  window.__releaseAssuranceDemoDirectorInstalled = true;
  new DemoDirector().install();
};

export { installDemoDirector };
