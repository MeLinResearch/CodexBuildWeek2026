import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import codexAvatarUrl from '@/assets/avatar-codex.png';
import melindaAvatarUrl from '@/assets/avatar-melinda.png';
import pivanovAvatarUrl from '@/assets/avatar-pivanov.png';
import cursorUrl from '@/assets/cursor.svg';
import pointingHandUrl from '@/assets/pointinghand.svg';
import { SPEAKER_LABELS, type TDirectorSpeaker } from '@/components/director/script';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

const CHAT_MESSAGE_LIMIT = 14;

interface IDirectorCaptionWord {
  id: string;
  text: string;
}

interface IDirectorChatMessage {
  activeWordIndex: number;
  complete: boolean;
  id: number;
  speaker: TDirectorSpeaker;
  text: string;
  words: IDirectorCaptionWord[] | null;
}

interface IDirectorChatGroup {
  messages: IDirectorChatMessage[];
  speaker: TDirectorSpeaker;
}

interface IDirectorChatActions {
  appendCaption: (speaker: TDirectorSpeaker, words: string[]) => number;
  appendText: (speaker: TDirectorSpeaker, text: string) => void;
  completeCaption: (messageId: number) => void;
  reset: () => void;
  setCaptionWordIndex: (messageId: number, wordIndex: number) => void;
}

interface IDemoDirectorOverlayElements {
  chat: IDirectorChatActions;
  cursor: HTMLDivElement;
  host: HTMLDivElement;
  panel: HTMLDivElement;
  status: HTMLDivElement;
  timer: HTMLTimeElement;
  timerValue: HTMLSpanElement;
}

let registeredElements: IDemoDirectorOverlayElements | null = null;

const getDemoDirectorOverlayElements = (): IDemoDirectorOverlayElements => {
  if (!registeredElements) {
    throw new Error('Demo director overlay is not mounted');
  }

  return registeredElements;
};

const team = [
  { speaker: 'melinda', label: 'MELINDA', avatarUrl: melindaAvatarUrl },
  { speaker: 'codex', label: 'CODEX', avatarUrl: codexAvatarUrl },
  { speaker: 'pivanov', label: 'PAVEL', avatarUrl: pivanovAvatarUrl },
] as const;

const speakerColors: Record<TDirectorSpeaker, string> = {
  codex: 'text-[#8fd0ff]',
  melinda: 'text-[#a49cff]',
  pivanov: 'text-[#ffc9a3]',
};

const directorWaveBars = [
  { className: 'h-[3px] w-px animate-director-wave rounded-sm bg-white [animation-delay:-.3s]', id: 'outer-left' },
  { className: 'h-1.5 w-px animate-director-wave rounded-sm bg-white [animation-delay:-.12s]', id: 'inner-left' },
  { className: 'h-[9px] w-px animate-director-wave rounded-sm bg-white', id: 'center' },
  { className: 'h-1.5 w-px animate-director-wave rounded-sm bg-white [animation-delay:-.12s]', id: 'inner-right' },
  { className: 'h-[3px] w-px animate-director-wave rounded-sm bg-white [animation-delay:-.3s]', id: 'outer-right' },
] as const;

const DirectorChatLine = ({ message }: { message: IDirectorChatMessage }) => {
  return (
    <div className="flex w-full animate-director-message-in flex-wrap gap-x-[.28em] gap-y-0.5">
      {message.words
        ? message.words.map((word, index) => {
            const state = message.complete || index < message.activeWordIndex ? 'spoken' : index === message.activeWordIndex ? 'active' : 'upcoming';

            return (
              <span
                key={word.id}
                data-state={state}
                className="text-[#c7cad4] opacity-0 transition-[opacity,color,text-shadow] duration-150 data-[state=spoken]:opacity-100 data-[state=active]:text-white data-[state=active]:text-shadow-[0_0_11px_rgba(145,134,255,.9)] data-[state=active]:opacity-100"
              >
                {word.text}
              </span>
            );
          })
        : message.text}
    </div>
  );
};

const DirectorChatGroup = ({ group }: { group: IDirectorChatGroup }) => {
  return (
    <div className="flex flex-col gap-[3px]">
      <div className={cn('font-mono text-[8px] leading-none font-bold tracking-[.09em] uppercase', speakerColors[group.speaker])}>
        {SPEAKER_LABELS[group.speaker]}
      </div>
      <div className="flex flex-col gap-1.5 rounded-[3px_12px_12px_12px] border border-[#857aff]/15 bg-[#857aff]/9 px-2.5 py-[7px] text-[11.5px] leading-[1.45] font-medium text-[#eef0f5]">
        {group.messages.map((message) => (
          <DirectorChatLine key={message.id} message={message} />
        ))}
      </div>
    </div>
  );
};

const DemoDirectorOverlayView = () => {
  const [messages, setMessages] = useState<IDirectorChatMessage[]>([]);
  const refMessageId = useRef(0);
  const refHost = useRef<HTMLDivElement>(null);
  const refPanel = useRef<HTMLDivElement>(null);
  const refChatViewport = useRef<HTMLDivElement>(null);
  const refStatus = useRef<HTMLDivElement>(null);
  const refTimer = useRef<HTMLTimeElement>(null);
  const refTimerValue = useRef<HTMLSpanElement>(null);
  const refCursor = useRef<HTMLDivElement>(null);

  const appendText = useCallback((speaker: TDirectorSpeaker, text: string): void => {
    const message: IDirectorChatMessage = {
      activeWordIndex: -1,
      complete: true,
      id: refMessageId.current++,
      speaker,
      text,
      words: null,
    };
    setMessages((current) => [...current, message].slice(-CHAT_MESSAGE_LIMIT));
  }, []);

  const appendCaption = useCallback((speaker: TDirectorSpeaker, words: string[]): number => {
    const id = refMessageId.current++;
    const captionWords = words.map((text, index) => ({ id: `${id}-word-${index}`, text }));
    const message: IDirectorChatMessage = {
      activeWordIndex: -1,
      complete: false,
      id,
      speaker,
      text: words.join(' '),
      words: captionWords,
    };
    setMessages((current) => [...current, message].slice(-CHAT_MESSAGE_LIMIT));
    return id;
  }, []);

  const setCaptionWordIndex = useCallback((messageId: number, wordIndex: number): void => {
    setMessages((current) => current.map((message) => (message.id === messageId ? { ...message, activeWordIndex: wordIndex } : message)));
  }, []);

  const completeCaption = useCallback((messageId: number): void => {
    setMessages((current) => current.map((message) => (message.id === messageId ? { ...message, complete: true } : message)));
  }, []);

  const reset = useCallback((): void => {
    refMessageId.current = 0;
    setMessages([]);
  }, []);

  const chat = useMemo<IDirectorChatActions>(
    () => ({ appendCaption, appendText, completeCaption, reset, setCaptionWordIndex }),
    [appendCaption, appendText, completeCaption, reset, setCaptionWordIndex],
  );
  const messageGroups = useMemo<IDirectorChatGroup[]>(() => {
    return messages.reduce<IDirectorChatGroup[]>((groups, message) => {
      const previous = groups.at(-1);

      if (previous?.speaker === message.speaker) {
        previous.messages.push(message);
      } else {
        groups.push({ messages: [message], speaker: message.speaker });
      }

      return groups;
    }, []);
  }, [messages]);
  const latestMessageId = messages.at(-1)?.id;

  useLayoutEffect(() => {
    if (latestMessageId === undefined) {
      return;
    }

    const viewport = refChatViewport.current;

    if (viewport) {
      viewport.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' });
    }
  }, [latestMessageId]);

  useLayoutEffect(() => {
    if (!refHost.current || !refPanel.current || !refStatus.current || !refTimer.current || !refTimerValue.current || !refCursor.current) {
      throw new Error('Demo director overlay did not initialize');
    }

    const elements: IDemoDirectorOverlayElements = {
      host: refHost.current,
      panel: refPanel.current,
      chat,
      status: refStatus.current,
      timer: refTimer.current,
      timerValue: refTimerValue.current,
      cursor: refCursor.current,
    };
    registeredElements = elements;

    return () => {
      if (registeredElements === elements) {
        registeredElements = null;
      }
    };
  }, [chat]);

  return createPortal(
    <div
      ref={refHost}
      id="release-assurance-demo-director"
      className="pointer-events-none fixed inset-0 z-2147483644 hidden font-sans text-[#f4f5f8] scheme-dark data-[active=true]:block"
      data-active="false"
      aria-live="polite"
    >
      <div
        ref={refPanel}
        className="group fixed bottom-[18px] left-[18px] z-2147483645 flex max-h-[min(34vh,320px)] w-[min(316px,calc(100vw-28px))] flex-col overflow-hidden rounded-[18px] border border-[#8289a0]/26 bg-[#090b11]/92 shadow-[0_24px_64px_rgba(0,0,0,.52)] backdrop-blur-lg"
        data-chat="hidden"
      >
        <div className="flex items-center justify-between gap-2.5 border-b border-transparent bg-[#857aff]/5 px-3.5 pt-[11px] pb-[9px] transition-colors group-data-[chat=revealing]:border-[#8289a0]/16 group-data-[chat=settled]:border-[#8289a0]/16 motion-reduce:transition-none">
          <div className="flex items-center gap-[7px]">
            {team.map(({ speaker, label, avatarUrl }) => (
              <div
                key={speaker}
                className="director-person relative w-11 text-center font-mono text-[7px] leading-none font-bold tracking-[.03em] text-[#717789] transition-colors data-[active=true]:text-[#f2f3f7] [&[data-active=true]_.director-avatar]:border-[#857aff] [&[data-active=true]_.director-avatar]:shadow-[0_0_0_3px_rgba(133,122,255,.17),0_0_18px_rgba(133,122,255,.3)] [&[data-speaking=true]_.director-wave]:flex"
                data-speaker={speaker}
              >
                <img
                  className="director-avatar mx-auto mb-1 block size-[30px] rounded-full border border-[#373c4a] bg-linear-to-br from-[#252a36] to-[#171b24] object-cover select-none transition-[border-color,box-shadow]"
                  src={avatarUrl}
                  alt=""
                  draggable={false}
                />
                <span className="director-wave absolute top-[-3px] right-0.5 hidden size-4 items-center justify-center gap-px rounded-full border-2 border-[#090b11] bg-[#796df4]">
                  {directorWaveBars.map((bar) => (
                    <i key={bar.id} className={bar.className} />
                  ))}
                </span>
                {label}
              </div>
            ))}
          </div>
          <div
            ref={refStatus}
            className="flex items-center gap-[7px] font-mono text-[7px] leading-none font-bold tracking-eyebrow whitespace-nowrap text-[#73798b] uppercase before:size-1.5 before:rounded-full before:bg-[#45c5b4] before:shadow-[0_0_8px_rgba(69,197,180,.8)] before:content-[''] data-[tone=attention]:text-[#bab4ff] data-[tone=attention]:before:animate-pulse data-[tone=attention]:before:bg-[#8c80ff] data-[tone=attention]:before:shadow-[0_0_8px_rgba(140,128,255,.85)] data-[tone=error]:text-[#ff9aaa] data-[tone=error]:before:bg-[#ed6476] data-[tone=error]:before:shadow-[0_0_8px_rgba(237,100,118,.85)]"
            data-tone="normal"
          >
            Live director
          </div>
        </div>

        <ScrollArea
          refViewport={refChatViewport}
          viewportClassName="h-full"
          className="h-0 min-h-0 w-full shrink-0 overflow-hidden opacity-0 transition-[height,opacity] duration-420 ease-[cubic-bezier(.16,1,.3,1)] group-data-[chat=revealing]:h-24 group-data-[chat=revealing]:opacity-100 group-data-[chat=settled]:h-[min(26vh,250px)] group-data-[chat=settled]:opacity-100 group-data-[chat=settled]:transition-none motion-reduce:transition-none"
        >
          <div className="flex min-h-full flex-col gap-[9px] px-3.5 py-3">
            {messageGroups.map((group) => (
              <DirectorChatGroup key={group.messages[0]?.id} group={group} />
            ))}
          </div>
        </ScrollArea>
      </div>

      <time
        ref={refTimer}
        className="group/timer fixed right-[18px] bottom-[18px] z-2147483645 inline-flex h-[38px] min-w-[86px] animate-director-timer-in items-center gap-[9px] rounded-lg border border-[#8289a0]/28 bg-[#090b11]/90 px-[13px] font-mono text-[13px] leading-none font-bold tracking-normal text-[#f4f5f8] tabular-nums shadow-[0_14px_36px_rgba(0,0,0,.4)] backdrop-blur-[14px] motion-reduce:animate-none"
        data-running="true"
        dateTime="PT0S"
        aria-hidden="true"
      >
        <span className="size-[7px] shrink-0 rounded-full bg-[#ed6476] shadow-[0_0_10px_rgba(237,100,118,.75)] group-data-[running=false]/timer:bg-[#73798b] group-data-[running=false]/timer:shadow-none group-data-[running=true]/timer:animate-director-timer-live motion-reduce:animate-none" />
        <span ref={refTimerValue}>00:00</span>
      </time>

      <div
        ref={refCursor}
        className="group/cursor fixed top-0 left-0 z-2147483646 size-8 opacity-0 drop-shadow-[0_3px_4px_rgba(0,0,0,.72)] transition-[transform,opacity] duration-700 ease-[cubic-bezier(.16,1,.3,1)] data-[visible=false]:duration-150 data-[visible=true]:opacity-100"
        aria-hidden="true"
      >
        <span className="absolute -top-3.5 -left-3.5 size-7 scale-[.35] rounded-full border-2 border-[#8b80ff]/75 opacity-0 group-data-[clicking=true]/cursor:animate-director-click-ring" />
        <img
          className="absolute top-0 left-0 size-7 -translate-x-2 translate-y-[-5px] select-none transition-opacity group-data-[pointing=true]/cursor:opacity-0"
          src={cursorUrl}
          alt=""
          draggable={false}
        />
        <img
          className="absolute top-0 left-0 size-8 translate-x-[-13px] -translate-y-2 opacity-0 select-none transition-opacity group-data-[pointing=true]/cursor:opacity-100"
          src={pointingHandUrl}
          alt=""
          draggable={false}
        />
      </div>
    </div>,
    document.body,
  );
};

export type { IDirectorChatActions };
export { DemoDirectorOverlayView, getDemoDirectorOverlayElements };
