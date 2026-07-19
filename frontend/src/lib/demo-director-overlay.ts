import codexAvatarUrl from '@/assets/avatar-codex.webp';
import melindaAvatarUrl from '@/assets/avatar-melinda.png';
import pivanovAvatarUrl from '@/assets/avatar-pivanov.png';
import backgroundMusicUrl from '@/assets/background-music-soft-calm-335280.mp3';
import cursorUrl from '@/assets/cursor.svg';
import pointingHandUrl from '@/assets/pointinghand.svg';
import { buildTimedCaptionWords, captionWordIndexAt } from '@/lib/demo-director-captions';
import { type IDirectorLine, SPEAKER_LABELS, type TDirectorSpeaker } from '@/lib/demo-director-script';

const BACKGROUND_MUSIC_VOLUME = 0.3;
const CHAT_MESSAGE_LIMIT = 14;
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

const delay = (milliseconds: number): Promise<void> => {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
};

/* A floating podcast panel: the hosts sit in a rounded card on the
 * left of the screen and every narrated line lands as a chat bubble,
 * so the audience can re-read the conversation instead of watching a
 * single caption slot overwrite itself. */
class DemoDirectorOverlay {
  readonly host: HTMLDivElement;
  readonly shadow: ShadowRoot;
  readonly cursor: HTMLDivElement;

  private readonly panel: HTMLDivElement;
  private readonly chat: HTMLDivElement;
  private readonly status: HTMLDivElement;
  private readonly timer: HTMLTimeElement;
  private readonly timerValue: HTMLSpanElement;
  private readonly backgroundMusic: HTMLAudioElement;
  private currentAudio: HTMLAudioElement | null = null;
  private backgroundMusicStopTimer: number | null = null;
  private captionAnimationFrame: number | null = null;
  private activeWordElements: HTMLElement[] = [];
  private chatRevealPromise: Promise<void> | null = null;
  private timerInterval: number | null = null;
  private timerStartedAt = 0;

  constructor() {
    this.host = document.createElement('div');
    this.host.id = 'release-assurance-demo-director';
    this.host.setAttribute('aria-live', 'polite');
    this.shadow = this.host.attachShadow({ mode: 'open' });
    this.shadow.innerHTML = `
      <style>
        :host {
          all: initial;
          color-scheme: dark;
          font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        * { box-sizing: border-box; }
        .panel {
          position: fixed;
          left: 18px;
          bottom: 18px;
          z-index: 2147483645;
          width: min(316px, calc(100vw - 28px));
          max-height: min(34vh, 320px);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          border: 1px solid rgba(130, 137, 160, .26);
          border-radius: 18px;
          background: rgba(9, 11, 17, .92);
          backdrop-filter: blur(16px);
          box-shadow: 0 24px 64px rgba(0, 0, 0, .52);
          color: #f4f5f8;
        }
        .head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          padding: 11px 14px 9px;
          border-bottom: 1px solid transparent;
          background: rgba(133, 122, 255, .05);
          transition: border-color .2s ease;
        }
        .panel[data-chat-visible="true"] .head { border-bottom-color: rgba(130, 137, 160, .16); }
        .team { display: flex; align-items: center; gap: 7px; }
        .person {
          position: relative;
          width: 44px;
          color: #717789;
          text-align: center;
          font: 700 7px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
          letter-spacing: .03em;
          transition: color .2s ease;
        }
        .avatar {
          width: 30px;
          height: 30px;
          margin: 0 auto 4px;
          display: block;
          border: 1px solid #373c4a;
          border-radius: 50%;
          background: linear-gradient(145deg, #252a36, #171b24);
          object-fit: cover;
          transition: border-color .2s ease, box-shadow .2s ease;
          user-select: none;
        }
        .person[data-active="true"] { color: #f2f3f7; }
        .person[data-active="true"] .avatar {
          border-color: #857aff;
          box-shadow: 0 0 0 3px rgba(133, 122, 255, .17), 0 0 18px rgba(133, 122, 255, .3);
        }
        .wave {
          position: absolute;
          top: -3px;
          right: 2px;
          width: 16px;
          height: 16px;
          display: none;
          align-items: center;
          justify-content: center;
          gap: 1px;
          border: 2px solid #090b11;
          border-radius: 50%;
          background: #796df4;
        }
        .person[data-speaking="true"] .wave { display: flex; }
        .wave i {
          width: 1px;
          border-radius: 2px;
          background: #fff;
          animation: wave .62s ease-in-out infinite alternate;
        }
        .wave i:nth-child(1), .wave i:nth-child(5) { height: 3px; animation-delay: -.3s; }
        .wave i:nth-child(2), .wave i:nth-child(4) { height: 6px; animation-delay: -.12s; }
        .wave i:nth-child(3) { height: 9px; }
        @keyframes wave { to { transform: scaleY(.45); opacity: .68; } }
        .chat {
          flex: 0 0 auto;
          width: 100%;
          height: 0;
          min-height: 0;
          display: flex;
          flex-direction: column;
          gap: 9px;
          overflow: hidden;
          padding: 0 14px;
          opacity: 0;
          scroll-behavior: smooth;
          scrollbar-width: thin;
          scrollbar-color: rgba(130, 137, 160, .4) transparent;
          transition:
            height ${CHAT_REVEAL_DURATION_MS}ms cubic-bezier(.16, 1, .3, 1),
            padding ${CHAT_REVEAL_DURATION_MS}ms cubic-bezier(.16, 1, .3, 1),
            opacity .24s ease .1s;
        }
        .panel[data-chat-visible="true"] .chat {
          height: 96px;
          padding: 12px 14px 14px;
          opacity: 1;
        }
        .panel[data-chat-settled="true"] .chat {
          flex: 1 1 auto;
          height: auto;
          min-height: 96px;
          overflow-y: auto;
          transition: none;
        }
        .msg {
          display: flex;
          flex-direction: column;
          gap: 3px;
          animation: msg-in .3s cubic-bezier(.16, 1, .3, 1);
        }
        @keyframes msg-in {
          from { opacity: 0; transform: translateY(9px); }
          to { opacity: 1; transform: none; }
        }
        .msg-speaker {
          color: #a49cff;
          font: 760 8px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
          letter-spacing: .09em;
          text-transform: uppercase;
        }
        .msg[data-speaker="codex"] .msg-speaker { color: #8fd0ff; }
        .msg[data-speaker="pivanov"] .msg-speaker { color: #ffc9a3; }
        .msg-text {
          display: flex;
          flex-wrap: wrap;
          column-gap: .28em;
          row-gap: 2px;
          padding: 7px 10px;
          border: 1px solid rgba(133, 122, 255, .15);
          border-radius: 3px 12px 12px 12px;
          background: rgba(133, 122, 255, .09);
          color: #eef0f5;
          font: 500 11.5px/1.45 Inter, ui-sans-serif, system-ui, sans-serif;
        }
        .msg[data-kind="system"] .msg-text {
          border-color: rgba(130, 137, 160, .18);
          background: rgba(130, 137, 160, .09);
          color: #c6cad6;
        }
        /* Every word of the line is laid out from the start (so the
         * bubble never reflows) and becomes visible as it is spoken. */
        .caption-word {
          opacity: 0;
          color: #c7cad4;
          transition: opacity .18s ease, color .12s ease, text-shadow .12s ease;
        }
        .caption-word[data-state="spoken"] { opacity: 1; }
        .caption-word[data-state="active"] {
          opacity: 1;
          color: #fff;
          text-shadow: 0 0 11px rgba(145, 134, 255, .9);
        }
        .status {
          display: flex;
          align-items: center;
          gap: 7px;
          color: #73798b;
          font: 700 7px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
          letter-spacing: .08em;
          text-transform: uppercase;
          white-space: nowrap;
        }
        .status::before {
          content: "";
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #45c5b4;
          box-shadow: 0 0 8px rgba(69, 197, 180, .8);
        }
        .status[data-tone="attention"] { color: #bab4ff; }
        .status[data-tone="attention"]::before {
          background: #8c80ff;
          box-shadow: 0 0 8px rgba(140, 128, 255, .85);
          animation: pulse 1s ease-in-out infinite alternate;
        }
        .status[data-tone="error"] { color: #ff919f; }
        .status[data-tone="error"]::before { background: #ed6476; box-shadow: 0 0 8px rgba(237, 100, 118, .8); }
        @keyframes pulse { to { opacity: .42; } }
        .timer {
          position: fixed;
          right: 18px;
          bottom: 18px;
          z-index: 2147483645;
          display: inline-flex;
          align-items: center;
          gap: 9px;
          min-width: 86px;
          height: 38px;
          padding: 0 13px;
          border: 1px solid rgba(130, 137, 160, .28);
          border-radius: 8px;
          background: rgba(9, 11, 17, .9);
          backdrop-filter: blur(14px);
          box-shadow: 0 14px 36px rgba(0, 0, 0, .4);
          color: #f4f5f8;
          font: 700 13px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
          font-variant-numeric: tabular-nums;
          letter-spacing: 0;
          animation: timer-in .5s cubic-bezier(.16, 1, .3, 1) both;
        }
        .timer-dot {
          width: 7px;
          height: 7px;
          flex: none;
          border-radius: 50%;
          background: #ed6476;
          box-shadow: 0 0 10px rgba(237, 100, 118, .75);
        }
        .timer[data-running="true"] .timer-dot { animation: timer-live 1.2s ease-in-out infinite alternate; }
        .timer[data-running="false"] .timer-dot {
          background: #73798b;
          box-shadow: none;
        }
        @keyframes timer-in {
          from { opacity: 0; transform: translateY(12px) scale(.94); }
          to { opacity: 1; transform: none; }
        }
        @keyframes timer-live { to { opacity: .46; } }
        .cursor {
          position: fixed;
          top: 0;
          left: 0;
          z-index: 2147483646;
          width: 32px;
          height: 32px;
          pointer-events: none;
          opacity: 0;
          transform: translate3d(50vw, 50vh, 0);
          transition: transform .7s cubic-bezier(.16, 1, .3, 1), opacity .2s ease;
          filter: drop-shadow(0 3px 4px rgba(0, 0, 0, .72));
        }
        .cursor[data-visible="true"] { opacity: 1; }
        .cursor-icon {
          position: absolute;
          top: 0;
          left: 0;
          display: block;
          user-select: none;
          transition: opacity .08s ease;
        }
        .cursor-arrow {
          width: 28px;
          height: 28px;
          transform: translate(-8px, -5px);
        }
        .cursor-hand {
          width: 32px;
          height: 32px;
          opacity: 0;
          transform: translate(-13px, -8px);
        }
        .cursor[data-pointing="true"] .cursor-arrow { opacity: 0; }
        .cursor[data-pointing="true"] .cursor-hand { opacity: 1; }
        .cursor-ring {
          position: absolute;
          top: -14px;
          left: -14px;
          width: 28px;
          height: 28px;
          border: 2px solid rgba(139, 128, 255, .75);
          border-radius: 50%;
          opacity: 0;
          transform: scale(.35);
        }
        .cursor[data-clicking="true"] .cursor-ring { animation: click-ring .38s ease-out; }
        @keyframes click-ring {
          0% { opacity: .9; transform: scale(.35); }
          100% { opacity: 0; transform: scale(1.45); }
        }
        @media (prefers-reduced-motion: reduce) {
          .head, .chat { transition: none; }
          .timer { animation: none; }
          .timer-dot { animation: none !important; }
        }
      </style>
      <div class="panel" data-chat-visible="false" data-chat-settled="false">
        <div class="head">
          <div class="team">
            <div class="person" data-speaker="melinda">
              <img class="avatar" src="${melindaAvatarUrl}" alt="" draggable="false" />
              <span class="wave"><i></i><i></i><i></i><i></i><i></i></span>
              MELINDA
            </div>
            <div class="person" data-speaker="codex">
              <img class="avatar" src="${codexAvatarUrl}" alt="" draggable="false" />
              <span class="wave"><i></i><i></i><i></i><i></i><i></i></span>
              CODEX
            </div>
            <div class="person" data-speaker="pivanov">
              <img class="avatar" src="${pivanovAvatarUrl}" alt="" draggable="false" />
              <span class="wave"><i></i><i></i><i></i><i></i><i></i></span>
              PAVEL
            </div>
          </div>
          <div class="status" data-tone="normal">Live director</div>
        </div>
        <div class="chat"></div>
      </div>
      <time class="timer" data-running="true" datetime="PT0S" aria-hidden="true">
        <span class="timer-dot"></span>
        <span class="timer-value">00:00</span>
      </time>
      <div class="cursor" aria-hidden="true">
        <span class="cursor-ring"></span>
        <img class="cursor-icon cursor-arrow" src="${cursorUrl}" alt="" draggable="false" />
        <img class="cursor-icon cursor-hand" src="${pointingHandUrl}" alt="" draggable="false" />
      </div>
    `;
    document.body.append(this.host);

    const panel = this.shadow.querySelector<HTMLDivElement>('.panel');
    const chat = this.shadow.querySelector<HTMLDivElement>('.chat');
    const status = this.shadow.querySelector<HTMLDivElement>('.status');
    const timer = this.shadow.querySelector<HTMLTimeElement>('.timer');
    const timerValue = this.shadow.querySelector<HTMLSpanElement>('.timer-value');
    const cursor = this.shadow.querySelector<HTMLDivElement>('.cursor');

    if (!panel || !chat || !status || !timer || !timerValue || !cursor) {
      throw new Error('Demo director overlay did not initialize');
    }

    this.panel = panel;
    this.chat = chat;
    this.status = status;
    this.timer = timer;
    this.timerValue = timerValue;
    this.cursor = cursor;
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
    this.appendMessage(speaker, 'line').textContent = text;
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
      if (!audio.ended) {
        audio.pause();
      }
      this.currentAudio = null;
      URL.revokeObjectURL(objectUrl);
    }
  }

  async moveCursorTo(element: HTMLElement, click = false): Promise<void> {
    const bounds = element.getBoundingClientRect();
    const x = Math.round(bounds.left + Math.min(bounds.width * 0.62, bounds.width - 8));
    const y = Math.round(bounds.top + Math.min(bounds.height * 0.55, bounds.height - 6));

    this.cursor.dataset.pointing = 'false';
    this.cursor.dataset.visible = 'true';
    this.cursor.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    await delay(760);

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
      this.currentAudio.pause();
      this.currentAudio = null;
    }
  }

  private stopBackgroundMusic(): void {
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

    this.panel.dataset.chatVisible = 'true';
    const transition = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? Promise.resolve() : delay(CHAT_REVEAL_DURATION_MS);
    this.chatRevealPromise = transition.then(() => {
      this.panel.dataset.chatSettled = 'true';
    });
    return this.chatRevealPromise;
  }

  private appendMessage(speaker: TDirectorSpeaker | null, kind: 'line' | 'system'): HTMLDivElement {
    const message = document.createElement('div');
    message.className = 'msg';
    message.dataset.kind = kind;

    if (speaker) {
      message.dataset.speaker = speaker;
    }

    const label = document.createElement('div');
    label.className = 'msg-speaker';
    label.textContent = speaker ? SPEAKER_LABELS[speaker] : 'Demo director';
    const text = document.createElement('div');
    text.className = 'msg-text';
    message.append(label, text);
    this.chat.append(message);

    while (this.chat.children.length > CHAT_MESSAGE_LIMIT) {
      this.chat.firstElementChild?.remove();
    }

    this.scrollChatToLatest();
    return text;
  }

  private scrollChatToLatest(): void {
    this.chat.scrollTop = this.chat.scrollHeight;
  }

  private setSpeakerActivity(speaker: TDirectorSpeaker, speaking: boolean): void {
    for (const person of this.shadow.querySelectorAll<HTMLElement>('.person')) {
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

  private fadeAudioVolume(audio: HTMLAudioElement, targetVolume: number, durationMs: number): Promise<void> {
    const initialVolume = audio.volume;
    const startedAt = performance.now();

    return new Promise((resolve) => {
      const timer = window.setInterval(() => {
        if (audio.ended || audio.paused) {
          window.clearInterval(timer);
          resolve();
          return;
        }

        const progress = Math.min(1, (performance.now() - startedAt) / durationMs);
        audio.volume = initialVolume + (targetVolume - initialVolume) * progress;

        if (progress >= 1) {
          window.clearInterval(timer);
          resolve();
        }
      }, 16);
    });
  }

  private startCaptionSync(speaker: TDirectorSpeaker, text: string, audio: HTMLAudioElement): void {
    this.stopCaptionSync();
    this.setSpeakerActivity(speaker, true);
    const target = this.appendMessage(speaker, 'line');
    const words = buildTimedCaptionWords(text, audio.duration);

    if (words.length === 0) {
      target.textContent = text;
      return;
    }

    const elements = words.map((word) => {
      const element = document.createElement('span');
      element.className = 'caption-word';
      element.textContent = word.text;
      element.dataset.state = 'upcoming';
      return element;
    });
    target.replaceChildren(...elements);
    this.activeWordElements = elements;
    this.scrollChatToLatest();

    const render = (): void => {
      const activeIndex = captionWordIndexAt(words, audio.currentTime);

      for (const [index, element] of elements.entries()) {
        element.dataset.state = index < activeIndex ? 'spoken' : index === activeIndex ? 'active' : 'upcoming';
      }

      this.captionAnimationFrame = window.requestAnimationFrame(render);
    };

    render();
  }

  private finishCaptionSync(speaker: TDirectorSpeaker): void {
    this.stopCaptionSync();

    for (const word of this.activeWordElements) {
      word.dataset.state = 'spoken';
    }

    this.activeWordElements = [];
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
