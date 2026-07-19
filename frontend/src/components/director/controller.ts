import backgroundMusicUrl from '@/assets/background-music-soft-calm-335280.mp3';
import { buildTimedCaptionWords, captionWordIndexAt } from '@/components/director/captions';
import { getDemoDirectorOverlayElements, type IDirectorChatActions } from '@/components/director/overlay';
import { type IDirectorLine, type TDirectorSpeaker } from '@/components/director/script';

const BACKGROUND_MUSIC_VOLUME = 0.3;
const BACKGROUND_MUSIC_DUCKED_VOLUME = 0.12;
const BACKGROUND_MUSIC_RELEASE_HOLD_MS = 500;
const CHAT_REVEAL_DURATION_MS = 420;

interface IPreparedSpeech {
  line: IDirectorLine;
  audio: HTMLAudioElement;
  objectUrl: string;
}

interface IPreparedPlaybackOptions {
  fadeInMs?: number;
  initialVolume?: number;
  pauseBeforeMs?: number;
  targetVolume?: number;
}

interface ICursorMoveOptions {
  travelMs?: number;
  xRatio?: number;
  yRatio?: number;
}

interface IActiveVolumeFade {
  finish: () => void;
  timer: number;
}

const delay = (milliseconds: number): Promise<void> => {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
};

/* Audio and choreography adapter for the React-rendered overlay. The
 * visual shell and messages live in overlay.tsx; this class sends
 * word-level progress and controls browser media plus cursor timing. */
class DemoDirectorOverlay {
  readonly host: HTMLDivElement;
  readonly cursor: HTMLDivElement;

  private readonly panel: HTMLDivElement;
  private readonly chat: IDirectorChatActions;
  private readonly status: HTMLDivElement;
  private readonly timer: HTMLTimeElement;
  private readonly timerValue: HTMLSpanElement;
  private readonly backgroundMusic: HTMLAudioElement;
  private readonly activeVolumeFades = new Map<HTMLAudioElement, IActiveVolumeFade>();
  private currentAudio: HTMLAudioElement | null = null;
  private backgroundMusicReleaseTimer: number | null = null;
  private backgroundMusicStopTimer: number | null = null;
  private captionAnimationFrame: number | null = null;
  private activeCaptionMessageId: number | null = null;
  private activeCaptionWordIndex = -1;
  private chatRevealPromise: Promise<void> | null = null;
  private timerInterval: number | null = null;
  private timerStartedAt = 0;

  constructor() {
    const elements = getDemoDirectorOverlayElements();
    this.host = elements.host;
    this.panel = elements.panel;
    this.chat = elements.chat;
    this.status = elements.status;
    this.timer = elements.timer;
    this.timerValue = elements.timerValue;
    this.cursor = elements.cursor;

    this.host.dataset.active = 'true';
    this.panel.dataset.chat = 'hidden';
    this.chat.reset();
    this.status.textContent = 'Live director';
    this.status.dataset.tone = 'normal';
    this.timer.dataset.running = 'true';
    this.cursor.dataset.visible = 'false';
    this.cursor.dataset.pointing = 'false';
    this.cursor.dataset.clicking = 'false';
    this.timerStartedAt = performance.now();
    this.updateTimer();
    this.timerInterval = window.setInterval(this.updateTimer, 250);

    this.backgroundMusic = new Audio(backgroundMusicUrl);
    this.backgroundMusic.loop = true;
    this.backgroundMusic.preload = 'auto';
    this.backgroundMusic.volume = BACKGROUND_MUSIC_VOLUME;
    void this.backgroundMusic.play().catch(() => {
      this.backgroundMusic.currentTime = 0;
    });
  }

  setStatus(text: string, tone: 'normal' | 'attention' | 'error' = 'normal'): void {
    this.status.textContent = text;
    this.status.dataset.tone = tone;
  }

  async setCaption(speaker: TDirectorSpeaker, text: string, speaking: boolean): Promise<void> {
    await this.revealChat();
    this.stopCaptionSync();
    this.chat.appendText(speaker, text);
    this.setSpeakerActivity(speaker, speaking);
  }

  /* Synthesis and playback are split so the director can generate the
   * next narration while the current one is still speaking; a coupled
   * speak() would spend every synthesis round-trip in on-screen
   * silence. */
  async prepareSpeech(line: IDirectorLine): Promise<IPreparedSpeech> {
    return this.prepareRuntimeSpeech(line);
  }

  /* Recording-day resilience: if synthesis for one line fails, the
   * walkthrough keeps moving with a timed caption instead of dying
   * mid-recording. */
  async showCaptionOnly(line: IDirectorLine, onPlaybackStarted?: () => void | Promise<void>): Promise<void> {
    await this.setCaption(line.speaker, line.text, true);
    this.setStatus('Voice unavailable, captions only', 'attention');
    const wordCount = line.text.trim().split(/\s+/u).filter(Boolean).length;
    const hold = delay(Math.max(2_800, wordCount * 320));
    await Promise.all([hold, Promise.resolve(onPlaybackStarted?.())]);
    this.setSpeakerActivity(line.speaker, false);
    this.setStatus('Following UI');
  }

  async playPrepared(
    prepared: IPreparedSpeech,
    onPlaybackStarted?: () => void | Promise<void>,
    options: IPreparedPlaybackOptions = {},
  ): Promise<void> {
    const { line, audio, objectUrl } = prepared;
    this.currentAudio = audio;

    try {
      const playbackEnded = new Promise<void>((resolve, reject) => {
        audio.addEventListener('ended', () => resolve(), { once: true });
        audio.addEventListener('error', () => reject(new Error('Runtime director speech failed')), { once: true });
      });

      await this.revealChat();
      this.setBackgroundMusicDucked(true);
      this.startCaptionSync(line.speaker, line.text, audio);
      this.setStatus('Speaking');
      audio.volume = options.initialVolume ?? (options.fadeInMs ? 0 : 1);
      await audio.play();

      const finishPlayback = playbackEnded.then(() => {
        this.finishCaptionSync(line.speaker);
        this.setStatus('Following UI');
      });
      const fadeIn = options.fadeInMs ? this.fadeAudioVolume(audio, options.targetVolume ?? 1, options.fadeInMs) : Promise.resolve();
      await Promise.all([finishPlayback, fadeIn, Promise.resolve(onPlaybackStarted?.())]);
    } finally {
      this.stopCaptionSync();
      this.setBackgroundMusicDucked(false);
      if (!audio.ended) {
        audio.pause();
      }
      this.currentAudio = null;
      URL.revokeObjectURL(objectUrl);
    }
  }

  async moveCursorTo(element: HTMLElement, click = false, options: ICursorMoveOptions = {}): Promise<void> {
    const bounds = element.getBoundingClientRect();
    const xRatio = options.xRatio ?? 0.62;
    const yRatio = options.yRatio ?? 0.55;
    const targetX = bounds.left + Math.max(8, Math.min(bounds.width * xRatio, bounds.width - 8));
    const targetY = bounds.top + Math.max(6, Math.min(bounds.height * yRatio, bounds.height - 6));
    const x = Math.round(Math.max(20, Math.min(window.innerWidth - 36, targetX)));
    const y = Math.round(Math.max(20, Math.min(window.innerHeight - 36, targetY)));

    this.cursor.dataset.pointing = 'false';
    this.cursor.dataset.visible = 'true';
    this.cursor.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    await delay(options.travelMs ?? 760);

    if (!click) {
      return;
    }

    this.cursor.dataset.pointing = 'true';
    await delay(90);
    this.cursor.dataset.clicking = 'true';
    element.click();
    await delay(420);
    this.cursor.dataset.clicking = 'false';
    this.cursor.dataset.pointing = 'false';
  }

  hideCursor(): void {
    this.cursor.dataset.visible = 'false';
    this.cursor.dataset.pointing = 'false';
  }

  stopAudio(): void {
    if (this.backgroundMusicStopTimer !== null) {
      window.clearTimeout(this.backgroundMusicStopTimer);
      this.backgroundMusicStopTimer = null;
    }

    this.stopCurrentSpeech();
    this.stopBackgroundMusic();
  }

  finishWithMusicTail(durationMs: number, onFinished?: () => void): void {
    this.stopCurrentSpeech();

    if (this.backgroundMusicStopTimer !== null) {
      window.clearTimeout(this.backgroundMusicStopTimer);
    }

    this.backgroundMusicStopTimer = window.setTimeout(() => {
      this.backgroundMusicStopTimer = null;
      void this.fadeAudioVolume(this.backgroundMusic, 0, 1_200).finally(() => {
        this.stopBackgroundMusic();
        onFinished?.();
      });
    }, durationMs);
  }

  private stopCurrentSpeech(): void {
    this.stopCaptionSync();
    if (this.currentAudio) {
      this.cancelVolumeFade(this.currentAudio);
      this.currentAudio.pause();
      this.currentAudio = null;
    }
  }

  private stopBackgroundMusic(): void {
    if (this.backgroundMusicReleaseTimer !== null) {
      window.clearTimeout(this.backgroundMusicReleaseTimer);
      this.backgroundMusicReleaseTimer = null;
    }

    this.cancelVolumeFade(this.backgroundMusic);
    this.backgroundMusic.pause();
    this.backgroundMusic.currentTime = 0;
    this.backgroundMusic.volume = BACKGROUND_MUSIC_VOLUME;
  }

  stopTimer(): void {
    this.updateTimer();

    if (this.timerInterval !== null) {
      window.clearInterval(this.timerInterval);
      this.timerInterval = null;
    }

    this.timer.dataset.running = 'false';
  }

  private readonly updateTimer = (): void => {
    const elapsedSeconds = Math.max(0, Math.floor((performance.now() - this.timerStartedAt) / 1_000));
    const minutes = Math.floor(elapsedSeconds / 60);
    const seconds = elapsedSeconds % 60;
    this.timerValue.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    this.timer.dateTime = `PT${elapsedSeconds}S`;
  };

  private revealChat(): Promise<void> {
    if (this.chatRevealPromise) {
      return this.chatRevealPromise;
    }

    this.panel.dataset.chat = 'revealing';
    const transition = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? Promise.resolve() : delay(CHAT_REVEAL_DURATION_MS);
    this.chatRevealPromise = transition.then(() => {
      this.panel.dataset.chat = 'settled';
    });
    return this.chatRevealPromise;
  }

  private setSpeakerActivity(speaker: TDirectorSpeaker, speaking: boolean): void {
    for (const person of this.host.querySelectorAll<HTMLElement>('.director-person')) {
      const active = person.dataset.speaker === speaker;
      person.dataset.active = String(active);
      person.dataset.speaking = String(active && speaking);
    }
  }

  private async prepareRuntimeSpeech(line: IDirectorLine): Promise<IPreparedSpeech> {
    const response = await fetch('/api/director/speech', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(line),
    });

    if (!response.ok) {
      throw new Error(`Runtime voice failed with HTTP ${response.status}`);
    }

    const audioBlob = await response.blob();
    if (audioBlob.size === 0) {
      throw new Error('Runtime voice response did not contain audio');
    }

    const objectUrl = URL.createObjectURL(audioBlob);
    try {
      const audio = new Audio(objectUrl);
      audio.preload = 'auto';
      audio.volume = 1;
      await this.waitForAudioMetadata(audio);
      return { line, audio, objectUrl };
    } catch (error) {
      URL.revokeObjectURL(objectUrl);
      throw error;
    }
  }

  private waitForAudioMetadata(audio: HTMLAudioElement): Promise<void> {
    if (audio.readyState >= HTMLMediaElement.HAVE_METADATA && Number.isFinite(audio.duration)) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const timeout = window.setTimeout(() => {
        cleanup();
        reject(new Error('Runtime director speech metadata timed out'));
      }, 5_000);
      const cleanup = (): void => {
        window.clearTimeout(timeout);
        audio.removeEventListener('loadedmetadata', handleMetadata);
        audio.removeEventListener('error', handleError);
      };
      const handleMetadata = (): void => {
        cleanup();
        if (!Number.isFinite(audio.duration) || audio.duration <= 0) {
          reject(new Error('Runtime director speech duration is invalid'));
          return;
        }
        resolve();
      };
      const handleError = (): void => {
        cleanup();
        reject(new Error('Runtime director speech failed to load'));
      };

      audio.addEventListener('loadedmetadata', handleMetadata, { once: true });
      audio.addEventListener('error', handleError, { once: true });
      audio.load();
    });
  }

  /* Sidechain feel: the music steps aside while someone talks and
   * breathes back up in the gaps. */
  private setBackgroundMusicDucked(ducked: boolean): void {
    if (this.backgroundMusic.paused) {
      return;
    }

    if (this.backgroundMusicReleaseTimer !== null) {
      window.clearTimeout(this.backgroundMusicReleaseTimer);
      this.backgroundMusicReleaseTimer = null;
    }

    if (ducked) {
      void this.fadeAudioVolume(this.backgroundMusic, BACKGROUND_MUSIC_DUCKED_VOLUME, 180);
      return;
    }

    this.backgroundMusicReleaseTimer = window.setTimeout(() => {
      this.backgroundMusicReleaseTimer = null;

      if (!this.backgroundMusic.paused) {
        void this.fadeAudioVolume(this.backgroundMusic, BACKGROUND_MUSIC_VOLUME, 600);
      }
    }, BACKGROUND_MUSIC_RELEASE_HOLD_MS);
  }

  private cancelVolumeFade(audio: HTMLAudioElement): void {
    this.activeVolumeFades.get(audio)?.finish();
  }

  private fadeAudioVolume(audio: HTMLAudioElement, targetVolume: number, durationMs: number): Promise<void> {
    this.cancelVolumeFade(audio);
    const initialVolume = audio.volume;
    const startedAt = performance.now();

    return new Promise((resolve) => {
      let finished = false;
      const finish = (): void => {
        if (finished) {
          return;
        }

        finished = true;
        const active = this.activeVolumeFades.get(audio);

        if (active) {
          window.clearInterval(active.timer);
          this.activeVolumeFades.delete(audio);
        }

        resolve();
      };
      const timer = window.setInterval(() => {
        if (audio.ended || audio.paused) {
          finish();
          return;
        }

        const progress = Math.min(1, (performance.now() - startedAt) / durationMs);
        audio.volume = initialVolume + (targetVolume - initialVolume) * progress;

        if (progress >= 1) {
          audio.volume = targetVolume;
          finish();
        }
      }, 16);
      this.activeVolumeFades.set(audio, { finish, timer });
    });
  }

  private startCaptionSync(speaker: TDirectorSpeaker, text: string, audio: HTMLAudioElement): void {
    this.stopCaptionSync();
    this.setSpeakerActivity(speaker, true);
    const words = buildTimedCaptionWords(text, audio.duration);

    if (words.length === 0) {
      this.chat.appendText(speaker, text);
      return;
    }

    this.activeCaptionMessageId = this.chat.appendCaption(
      speaker,
      words.map((word) => word.text),
    );
    this.activeCaptionWordIndex = -1;

    const render = (): void => {
      const activeIndex = captionWordIndexAt(words, audio.currentTime);

      if (this.activeCaptionMessageId !== null && activeIndex !== this.activeCaptionWordIndex) {
        this.activeCaptionWordIndex = activeIndex;
        this.chat.setCaptionWordIndex(this.activeCaptionMessageId, activeIndex);
      }

      this.captionAnimationFrame = window.requestAnimationFrame(render);
    };

    render();
  }

  private finishCaptionSync(speaker: TDirectorSpeaker): void {
    this.stopCaptionSync();

    if (this.activeCaptionMessageId !== null) {
      this.chat.completeCaption(this.activeCaptionMessageId);
    }

    this.activeCaptionMessageId = null;
    this.activeCaptionWordIndex = -1;
    this.setSpeakerActivity(speaker, false);
  }

  private stopCaptionSync(): void {
    if (this.captionAnimationFrame !== null) {
      window.cancelAnimationFrame(this.captionAnimationFrame);
      this.captionAnimationFrame = null;
    }
  }
}

export type { IPreparedPlaybackOptions, IPreparedSpeech };
export { DemoDirectorOverlay, delay };
