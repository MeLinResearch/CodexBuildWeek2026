import { refAppViewport } from '@/lib/app-viewport';
import { DemoDirectorOverlay, delay, type IPreparedPlaybackOptions, type IPreparedSpeech } from '@/components/director/controller';
import {
  CLOSE_LINES,
  constrainDirectorTurn,
  DIRECTOR_APPROVAL_NOTE,
  FALLBACK_LINES,
  type IDirectorLine,
  type IDirectorTurn,
  INTRO_LINES,
  isDirectorSpaceKey,
  isDirectorTurn,
  type TDirectorPhase,
  VERIFY_WAIT_LINE,
} from '@/components/director/script';
import { setDirectorTimelinePosition } from '@/components/director/timeline-sequence';
import { useRunUi } from '@/state/run-store';

const LIVE_RESULT_BUDGET_MS = 90_000;
const MUSIC_TAIL_MS = 20_000;
const RECORDING_BUDGET_MS = 175_000;
const STEP_TIMEOUT_MS = 45_000;
const VIEWPORT_BOTTOM_INSET_PX = 36;
const VIEWPORT_HEADER_GAP_PX = 12;

type TDirectorState = 'idle' | 'running' | 'complete' | 'failed';

interface IPhasePlaybackHooks {
  before?: () => Promise<void>;
  onFirstPlaybackStarted?: () => void | Promise<void>;
  onLinePlaybackStarted?: (index: number) => void | Promise<void>;
  afterLine?: (index: number) => void | Promise<void>;
  playbackOptions?: (index: number) => IPreparedPlaybackOptions;
}

/* A line whose audio failed to synthesize still plays as a timed
 * caption; one bad synthesis must never stop a recording. */
interface IPreparedLine {
  line: IDirectorLine;
  speech: IPreparedSpeech | null;
}

type TGeneratedDirectorPhase = Exclude<TDirectorPhase, 'intro'>;
type TDirectorDelivery = NonNullable<IDirectorLine['delivery']>;

const PHASE_DELIVERIES: Partial<Record<TGeneratedDirectorPhase, readonly TDirectorDelivery[]>> = {
  live_wait: ['wait_banter', 'wait_banter', 'wait_banter'],
  requirements: ['reveal_requirements'],
  failures: ['reveal_failures', 'reveal_failures'],
  traceability: ['reveal_traceability', 'reveal_traceability'],
  patch: ['patch_present'],
  review: ['review_request', 'review_codex_tease', 'review_melinda_reply'],
  approval: ['approval_decision', 'approval_note'],
  evidence: ['reveal_evidence', 'reveal_evidence'],
};

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

const scrollToElement = async (element: HTMLElement, block: ScrollLogicalPosition = 'nearest'): Promise<void> => {
  const viewport = refAppViewport.current;

  if (!viewport) {
    throw new Error('The application ScrollArea viewport is not mounted');
  }

  const scrollTargetFor = (alignment: ScrollLogicalPosition): number => {
    const viewportBounds = viewport.getBoundingClientRect();
    const elementBounds = element.getBoundingClientRect();
    const header = viewport.querySelector<HTMLElement>('[data-app-header]');
    const headerBottom = header?.getBoundingClientRect().bottom ?? viewportBounds.top;
    const safeTop = Math.max(viewportBounds.top, headerBottom) + VIEWPORT_HEADER_GAP_PX;
    const safeBottom = viewportBounds.bottom - VIEWPORT_BOTTOM_INSET_PX;
    const safeHeight = safeBottom - safeTop;
    let delta = 0;

    if (elementBounds.height >= safeHeight || alignment === 'start') {
      delta = elementBounds.top - safeTop;
    } else if (alignment === 'end') {
      delta = elementBounds.bottom - safeBottom;
    } else if (alignment === 'center') {
      delta = elementBounds.top + elementBounds.height / 2 - (safeTop + safeHeight / 2);
    } else if (elementBounds.top < safeTop) {
      delta = elementBounds.top - safeTop;
    } else if (elementBounds.bottom > safeBottom) {
      delta = elementBounds.bottom - safeBottom;
    }

    return Math.max(0, Math.min(viewport.scrollHeight - viewport.clientHeight, viewport.scrollTop + delta));
  };

  viewport.scrollTo({ top: scrollTargetFor(block), behavior: 'smooth' });
  await delay(520);
  viewport.scrollTo({ top: scrollTargetFor('nearest'), behavior: 'auto' });
  await delay(80);
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

const waitForDirectorObservation = async (id: string): Promise<HTMLElement> => {
  return waitForValue(() => document.getElementById(id), STEP_TIMEOUT_MS, `The ${id} observation did not become available`);
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
    document.documentElement.dataset.demoDirector = 'running';
    this.recordingStartedAt = performance.now();
    this.overlay = new DemoDirectorOverlay();
    void this.run(liveButton);
  };

  private async run(liveButton: HTMLButtonElement): Promise<void> {
    if (!this.overlay) {
      return;
    }

    try {
      this.overlay.setStatus('Going live…', 'attention');
      const intro: IDirectorTurn = { lines: [...INTRO_LINES] };
      const introPrepared = this.prepareTurn(intro);
      let waitingPrepared: Promise<IPreparedLine[]> | null = introPrepared.then(() => {
        return this.requestPreparedTurn(
          'live_wait',
          [
            'This narration will play only after the Run Live button has been clicked.',
            'At playback time the browser will show the live run as pending.',
            'GPT-5.6 and Codex will be running, but no result will be visible yet.',
          ],
          3,
        );
      });
      await this.queuePhasePlayback(introPrepared, {
        playbackOptions: (index) => {
          if (index === 0) {
            return { fadeInMs: 500, initialVolume: 0.45, targetVolume: 0.78 };
          }
          if (index === 1) {
            return { fadeInMs: 260, initialVolume: 0.78, targetVolume: 0.92 };
          }
          if (index === 2) {
            return { fadeInMs: 180, initialVolume: 0.92, targetVolume: 1 };
          }
          if (index === 3) {
            return { pauseBeforeMs: 450 };
          }
          return {};
        },
        onLinePlaybackStarted: async (index) => {
          if (index !== intro.lines.length - 1) {
            return;
          }

          await delay(1_800);
          this.overlay?.setStatus('Starting live run', 'attention');
          await this.overlay?.moveCursorTo(liveButton, true);
          this.overlay?.hideCursor();
          this.liveDeadline = performance.now() + LIVE_RESULT_BUDGET_MS;
        },
      });

      /* A live run spends thirty to ninety seconds inside one POST;
       * each waiting turn is generated and synthesized while the
       * previous turn is speaking, eliminating model-call silence. */
      while (!this.timelineIsReady() && performance.now() < this.liveDeadline) {
        const elapsedSeconds = Math.max(0, Math.round((performance.now() - this.liveDeadline + LIVE_RESULT_BUDGET_MS) / 1_000));
        const currentPrepared = await (waitingPrepared ??
          this.requestPreparedTurn(
            'live_wait',
            ['The live run is pending.', 'No timeline result is visible yet.', 'The director must not invent model progress.'],
            2,
          ));
        if (this.timelineIsReady()) {
          void this.releasePreparedTurn(Promise.resolve(currentPrepared));
          waitingPrepared = null;
          break;
        }

        const nextPrepared = this.requestPreparedTurn(
          'live_wait',
          [
            `About ${elapsedSeconds} seconds have passed since the live button was clicked.`,
            'The live run is still pending and the progress panel with the elapsed timer is visible.',
            'The director must not invent model progress.',
          ],
          2,
        );

        await this.playPreparedTurn(Promise.resolve(currentPrepared));

        if (this.timelineIsReady()) {
          void this.releasePreparedTurn(nextPrepared);
          waitingPrepared = null;
          break;
        }

        waitingPrepared = nextPrepared;
      }

      if (waitingPrepared) {
        void this.releasePreparedTurn(waitingPrepared);
      }

      await this.waitForLiveTimeline();
      await this.presentTimeline();
      this.state = 'complete';
      document.documentElement.dataset.demoDirector = 'music-tail';
      this.overlay.setStatus('Walkthrough complete · music tail');
      this.overlay.finishWithMusicTail(MUSIC_TAIL_MS, () => {
        document.documentElement.dataset.demoDirector = 'complete';
        this.overlay?.setStatus('Walkthrough complete');
      });
      this.overlay.stopTimer();
      this.overlay.hideCursor();
    } catch (error) {
      this.state = 'failed';
      this.aborted = true;
      document.documentElement.dataset.demoDirector = 'failed';
      const message = error instanceof Error ? error.message : 'The live walkthrough stopped unexpectedly';
      await this.overlay.setCaption('codex', message, false);
      this.overlay.setStatus('Director stopped', 'error');
      this.overlay.stopAudio();
      this.overlay.stopTimer();
      this.overlay.hideCursor();
    }
  }

  private async presentTimeline(): Promise<void> {
    const overlay = this.overlay;

    if (!overlay) {
      return;
    }

    setDirectorTimelinePosition(1);

    const requirementsPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'requirements',
        async () => [
          observedText(await waitForDirectorObservation('director-observation-requirements')),
          'The live control manifest is schema validated.',
        ],
        1,
      ),
      {
        before: async () => {
          setDirectorTimelinePosition(3);
          const step = await waitForStep('step-requirements', (element) => /REQ-\d{3}/.test(normalizedText(element)));
          await scrollToElement(step, 'start');
        },
      },
    );

    let firstFailedTestRow: HTMLElement | null = null;
    const failuresPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'failures',
        async () => [
          observedText(await waitForDirectorObservation('director-observation-failures')),
          'The deterministic checks completed with blocking failures.',
          'After Melinda reacts, Pavel points at the failed record on screen: exactly the kind of defect nobody catches by eye.',
        ],
        2,
      ),
      {
        before: async () => {
          setDirectorTimelinePosition(5);
          const step = await waitForStep(
            'step-tests',
            (element) => /TEST-\d{3}/.test(normalizedText(element)) && /failed/i.test(normalizedText(element)),
          );
          firstFailedTestRow = step.querySelector<HTMLElement>('[data-director-target="failed-test-row"]');
          await scrollToElement(step, 'start');
        },
        onLinePlaybackStarted: async (index) => {
          if (index === 1 && firstFailedTestRow) {
            await delay(650);
            await overlay.moveCursorTo(firstFailedTestRow);
          }
        },
      },
    );

    let traceabilityRows: HTMLElement[] = [];
    const traceabilityPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'traceability',
        async () => [
          observedText(await waitForDirectorObservation('director-observation-traceability')),
          'Each row links a requirement to its deterministic test, failure, and proposed patch.',
          'After Pavel explains the visible matrix, Codex briefly explains how it preserved the reasoning chain behind the scenes.',
        ],
        2,
      ),
      {
        before: async () => {
          overlay.hideCursor();
          setDirectorTimelinePosition(7);
          const step = await waitForStep('step-matrix', (element) => element.querySelector('table') !== null);
          traceabilityRows = Array.from(
            step.querySelectorAll<HTMLElement>('tbody tr[data-director-expandable="true"]'),
          );
          if (traceabilityRows.length === 0) {
            throw new Error('No expandable traceability rows became available');
          }
          await scrollToElement(step, 'start');
        },
        onLinePlaybackStarted: async (index) => {
          if (index !== 0) {
            return;
          }

          await delay(750);
          for (const row of traceabilityRows) {
            await scrollToElement(row, 'center');
            const shouldExpand = row.dataset.directorExpanded !== 'true';
            await overlay.moveCursorTo(row, shouldExpand, { xRatio: 0.3, yRatio: 0.5 });
            await delay(180);
          }
        },
      },
    );

    let patchFixLink: HTMLButtonElement | null = null;
    let patchDiffViewer: HTMLElement | null = null;
    const patchPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'patch',
        async () => [
          observedText(await waitForDirectorObservation('director-observation-patch')),
          'A complete read-only diff is visible for human review.',
          'On screen the cursor follows the fix link from the failed record straight into the complete diff.',
        ],
        1,
      ),
      {
        before: async () => {
          overlay.hideCursor();
          setDirectorTimelinePosition(9);
          const patchStep = await waitForStep('step-patch', (step) => /proposed by Codex/i.test(normalizedText(step)));
          patchFixLink = findVisibleButton(/^reconcile\//);
          patchDiffViewer = patchStep.querySelector<HTMLElement>('[data-director-target="diff-viewer"]');
        },
        onFirstPlaybackStarted: async () => {
          await delay(350);
          if (patchFixLink) {
            await scrollToElement(patchFixLink, 'center');
            await overlay.moveCursorTo(patchFixLink, true);
          }
          if (patchDiffViewer) {
            await scrollToElement(patchDiffViewer, 'start');
          }
        },
      },
    );

    let reviewDiffFile: HTMLElement | null = null;
    let reviewFileHeader: HTMLElement | null = null;
    let reviewDiffContent: HTMLElement | null = null;
    const reviewPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'review',
        async () => [
          observedText(await waitForDirectorObservation('director-observation-patch')),
          'The complete read-only diff is visible, and the cursor will inspect its header and changed lines.',
          'Use the required three-person review choreography while the cursor inspects the visible diff.',
        ],
        3,
      ),
      {
        before: async () => {
          overlay.hideCursor();
          setDirectorTimelinePosition(9);
          const patchStep = await waitForStep('step-patch', (step) => step.querySelector('[data-director-target="diff-viewer"]') !== null);
          reviewDiffFile = patchStep.querySelector<HTMLElement>('[data-director-target="diff-file"]');
          reviewFileHeader = patchStep.querySelector<HTMLElement>('[data-director-target="diff-file-header"]');
          reviewDiffContent = patchStep.querySelector<HTMLElement>('[data-director-target="diff-content"]');

          if (!reviewDiffFile || !reviewFileHeader || !reviewDiffContent) {
            throw new Error('The diff review targets did not become ready');
          }
        },
        onLinePlaybackStarted: async (index) => {
          if (index === 0 && reviewFileHeader) {
            await scrollToElement(reviewFileHeader, 'start');
            await overlay.moveCursorTo(reviewFileHeader, false, { xRatio: 0.28, yRatio: 0.5 });
            return;
          }

          if (index === 1 && reviewDiffContent) {
            await scrollToElement(reviewDiffContent, 'start');
            await overlay.moveCursorTo(reviewDiffContent, false, { xRatio: 0.38, yRatio: 0.25 });
            await delay(260);
            await overlay.moveCursorTo(reviewDiffContent, false, { xRatio: 0.68, yRatio: 0.48 });
            return;
          }

          if (index === 2 && reviewDiffFile && reviewDiffContent) {
            await scrollToElement(reviewDiffContent, 'start');
            await overlay.moveCursorTo(reviewDiffContent, false, { xRatio: 0.42, yRatio: 0.28 });
          }
        },
        afterLine: async (index) => {
          if (index === 2 && reviewDiffFile && reviewDiffContent) {
            await delay(350);
            await overlay.moveCursorTo(reviewDiffContent, false, { xRatio: 0.68, yRatio: 0.5 });
            await delay(300);
            await scrollToElement(reviewDiffFile, 'end');
            await overlay.moveCursorTo(reviewDiffContent, false, { xRatio: 0.45, yRatio: 0.76 });
          }
        },
      },
    );

    let approvalStep: HTMLElement | null = null;
    let approvalButton: HTMLButtonElement | null = null;
    let approvalDialog: HTMLElement | null = null;
    let approvalTextarea: HTMLTextAreaElement | null = null;
    const approvalPlayed = this.queuePhasePlayback(
      this.queuePhaseGeneration(
        'approval',
        async () => [
          observedText(await waitForDirectorObservation('director-observation-approval')),
          'Melinda has now double-checked the complete diff and chooses approval for this recorded demonstration.',
          'Melinda first announces her considered approval, then says she will add a clear review note.',
        ],
        2,
      ),
      {
        before: async () => {
          overlay.hideCursor();
          setDirectorTimelinePosition(10);
          approvalStep = await waitForValue(
            () => {
              const step = document.getElementById('step-decision');
              return step && findVisibleButton('Approve patch', step) ? step : null;
            },
            STEP_TIMEOUT_MS,
            'The human decision gate did not become ready',
          );
          approvalButton = findVisibleButton('Approve patch', approvalStep);
        },
        onLinePlaybackStarted: async (index) => {
          if (index === 0 && approvalButton && approvalStep) {
            await delay(500);
            await scrollToElement(approvalStep, 'end');
            await delay(300);
            await overlay.moveCursorTo(approvalButton);
            return;
          }

          if (index !== 1 || !approvalTextarea) {
            return;
          }

          for (let characterCount = 1; characterCount <= DIRECTOR_APPROVAL_NOTE.length; characterCount += 1) {
            setTextareaValue(approvalTextarea, DIRECTOR_APPROVAL_NOTE.slice(0, characterCount));
            await delay(12);
          }
        },
        afterLine: async (index) => {
          if (index === 0) {
            if (!approvalButton) {
              throw new Error('The Approve patch button is unavailable');
            }

            await overlay.moveCursorTo(approvalButton, true, { travelMs: 120 });
            approvalDialog = await waitForValue(
              () => {
                const dialog = document.querySelector<HTMLElement>('[data-slot="dialog-content"]');
                return dialog && isVisible(dialog) ? dialog : null;
              },
              STEP_TIMEOUT_MS,
              'The approval dialog did not open',
            );
            approvalTextarea = await waitForValue(
              () => approvalDialog?.querySelector<HTMLTextAreaElement>('textarea'),
              STEP_TIMEOUT_MS,
              'The approval note field did not become ready',
            );
            await overlay.moveCursorTo(approvalTextarea, true);
            return;
          }

          if (index !== 1 || !approvalDialog) {
            return;
          }

          const confirmButton = await waitForValue(
            () => {
              const button = findVisibleButton('Approve patch', approvalDialog ?? document);
              return button && !button.disabled ? button : null;
            },
            STEP_TIMEOUT_MS,
            'The approval note was not accepted',
          );
          await overlay.moveCursorTo(confirmButton, true);
          overlay.setStatus('Decision recorded · verifying patch', 'attention');
        },
      },
    );

    await Promise.all([requirementsPlayed, failuresPlayed, traceabilityPlayed, patchPlayed, reviewPlayed, approvalPlayed]);
    await waitForValue(
      () => {
        if (this.approvalFailed()) {
          throw new Error('The approval endpoint did not complete');
        }

        return useRunUi.getState().approval?.status === 'approved' ? true : null;
      },
      STEP_TIMEOUT_MS,
      'Melinda’s approval was not recorded',
    );
    const recordedDecision = await waitForValue(
      () => {
        const step = document.getElementById('step-decision');
        const record = step?.querySelector<HTMLElement>('[data-director-target="decision-record"]');
        return step && record ? { step, record } : null;
      },
      STEP_TIMEOUT_MS,
      'The recorded decision did not become visible',
    );
    overlay.hideCursor();
    await scrollToElement(recordedDecision.step, 'start');
    await overlay.moveCursorTo(recordedDecision.record, false, { xRatio: 0.25, yRatio: 0.35 });

    /* Scripted beat while the real apply-and-verify runs: the AI
     * teammate sweating its own patch, claiming nothing. */
    await this.playPreparedTurn(this.prepareTurn({ lines: [{ ...VERIFY_WAIT_LINE }] }));

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
    const evidencePrepared = this.queuePhaseGeneration(
      'evidence',
      async () => [
        observedText(evidenceStep),
        'The approved deterministic rerun passed in a disposable workspace.',
        'The verified suite contains 168 backend tests and 27 frontend tests.',
      ],
      2,
    );
    overlay.hideCursor();
    await scrollToElement(evidenceStep, 'end');
    const evidencePlayed = this.queuePhasePlayback(evidencePrepared);

    /* The close is scripted: the recording's final impression never
     * gambles on generation. It still synthesizes while the evidence
     * narration plays. */
    const closePrepared = this.generationTail.then(() => this.prepareTurn({ lines: CLOSE_LINES.map((line) => ({ ...line })) }));
    this.generationTail = closePrepared.then(
      () => undefined,
      () => undefined,
    );
    const closePlayed = this.queuePhasePlayback(closePrepared, {
      before: async () => {
        overlay.setStatus('168 backend · 27 frontend');
      },
      onFirstPlaybackStarted: async () => {
        const evidenceButton = findVisibleButton('Evidence pack');

        if (evidenceButton) {
          await overlay.moveCursorTo(evidenceButton);
        }
      },
    });

    await evidencePlayed;
    await closePlayed;
  }

  /* Chains a turn request plus per-line synthesis onto the generation
   * tail; resolves with playable audio (or caption fallbacks) for the
   * whole phase. */
  private queuePhaseGeneration(phase: TGeneratedDirectorPhase, observe: () => Promise<string[]>, maxLines: number): Promise<IPreparedLine[]> {
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

      const deliveries = PHASE_DELIVERIES[phase];
      return Promise.all(
        turn.lines.map((line, index) => {
          const delivery = deliveries?.[index] ?? line.delivery;
          return this.prepareLine(delivery ? { ...line, delivery } : line);
        }),
      );
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

  private async playLine(
    item: IPreparedLine,
    onPlaybackStarted?: () => void | Promise<void>,
    playbackOptions?: IPreparedPlaybackOptions,
  ): Promise<void> {
    const overlay = this.overlay;

    if (!overlay) {
      return;
    }

    if (playbackOptions?.pauseBeforeMs) {
      await delay(playbackOptions.pauseBeforeMs);
    }

    if (item.speech) {
      await overlay.playPrepared(item.speech, onPlaybackStarted, playbackOptions);
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

        const onPlaybackStarted =
          hooks?.onFirstPlaybackStarted || hooks?.onLinePlaybackStarted
            ? async () => {
                if (index === 0) {
                  await hooks?.onFirstPlaybackStarted?.();
                }

                await hooks?.onLinePlaybackStarted?.(index);
              }
            : undefined;
        await this.playLine(item, onPlaybackStarted, hooks?.playbackOptions?.(index));
        await hooks?.afterLine?.(index);
      }
    });
    this.playbackTail = playback.then(
      () => undefined,
      () => undefined,
    );
    return playback;
  }

  private async requestPreparedTurn(phase: TGeneratedDirectorPhase, observations: string[], maxLines: number): Promise<IPreparedLine[]> {
    const turn = await this.requestTurn(phase, observations, maxLines);
    return this.prepareTurn(turn);
  }

  private async prepareTurn(turn: IDirectorTurn): Promise<IPreparedLine[]> {
    for (const line of turn.lines) {
      this.pushHistory(line);
    }

    return Promise.all(turn.lines.map((line) => this.prepareLine(line)));
  }

  private async playPreparedTurn(preparedPromise: Promise<IPreparedLine[]>, onFirstPlaybackStarted?: () => void | Promise<void>): Promise<void> {
    const prepared = await preparedPromise;

    for (const [index, item] of prepared.entries()) {
      await this.playLine(item, index === 0 ? onFirstPlaybackStarted : undefined);
    }
  }

  private async releasePreparedTurn(preparedPromise: Promise<IPreparedLine[]>): Promise<void> {
    const prepared = await preparedPromise;

    for (const item of prepared) {
      if (item.speech) {
        URL.revokeObjectURL(item.speech.objectUrl);
      }
    }
  }

  private pushHistory(line: IDirectorLine): void {
    this.history.push(`${line.speaker}: ${line.text}`);

    if (this.history.length > 12) {
      this.history.shift();
    }
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
    setDirectorTimelinePosition(1);
    this.overlay.setStatus('Live result ready');
  }

  private async requestTurn(phase: TGeneratedDirectorPhase, observations: string[], maxLines: number): Promise<IDirectorTurn> {
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
      return constrainDirectorTurn(phase, payload);
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
    const text = document.body.textContent ?? '';
    return text.includes('The decision endpoint did not respond') || text.includes('the approved rerun did not complete');
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
