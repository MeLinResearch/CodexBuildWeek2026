import { ChevronRight } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { Fragment, type ReactNode, useState } from 'react';
import Markdown from 'react-markdown';

import { ScrollArea } from '@/components/ui/scroll-area';
import type { IDemo, IDemoInput } from '@/lib/demos';
import { cn } from '@/lib/utils';
import { staggerContainerVariants, staggerItemVariants } from '@/lib/variants';
import type { IDroppedFile } from '@/state/run-store';

const KIND_LABELS: Record<string, string> = {
  spec: 'conversion spec',
  data: 'source data',
  schema: 'target schema',
};

/* Naive split is fine for the demo CSVs (no quoted commas); anything
 * that does not parse cleanly falls back to plain text. */
const parseCsv = (content: string): string[][] | null => {
  const lines = content.trim().split('\n');

  if (lines.length < 2 || !lines[0]?.includes(',') || content.includes('"')) {
    return null;
  }

  return lines.map((line) => line.split(','));
};

const NUMERIC = /^-?\d+(\.\d+)?$/;

const CsvTable = ({ rows }: { rows: string[][] }) => {
  const [header, ...body] = rows;
  const numericColumns = (header ?? []).map((_, columnIndex) => body.every((row) => NUMERIC.test(row[columnIndex] ?? '')));

  return (
    <table className="w-full border-collapse font-mono text-3xs">
      <thead>
        <tr className="bg-muted/60">
          {header?.map((cell, columnIndex) => (
            <th
              key={cell}
              className={cn(
                'px-2.5 py-1.5 text-left font-semibold tracking-eyebrow whitespace-nowrap text-faint-foreground uppercase',
                numericColumns[columnIndex] && 'text-right',
              )}
            >
              {cell}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {body.map((row) => (
          <tr key={row.join(',')} className="border-b transition-colors last:border-b-0 hover:bg-muted/30">
            {row.map((cell, columnIndex) => (
              <td
                key={`${row[0]}-${header?.[columnIndex] ?? columnIndex}`}
                className={cn(
                  'px-2.5 py-1.5 whitespace-nowrap',
                  columnIndex === 0 && 'font-semibold',
                  numericColumns[columnIndex] && 'text-right tabular-nums',
                )}
              >
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

const JSON_TOKENS = /("(?:[^"\\]|\\.)*"\s*:)|("(?:[^"\\]|\\.)*")|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|\b(true|false|null)\b/g;

/* Tiny JSON-only highlighter: keys, strings, numbers, literals. */
const highlightJson = (source: string): ReactNode[] => {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let match = JSON_TOKENS.exec(source);
  let key = 0;

  while (match) {
    if (match.index > lastIndex) {
      nodes.push(<Fragment key={key++}>{source.slice(lastIndex, match.index)}</Fragment>);
    }

    const [token, jsonKey, string, number, literal] = match;
    const className = jsonKey
      ? 'text-primary dark:text-primary-subtle'
      : string
        ? 'text-success'
        : number
          ? 'text-warning'
          : literal
            ? 'text-info'
            : undefined;
    nodes.push(
      <span key={key++} className={className}>
        {token}
      </span>,
    );

    lastIndex = match.index + token.length;
    match = JSON_TOKENS.exec(source);
  }

  nodes.push(<Fragment key={key++}>{source.slice(lastIndex)}</Fragment>);
  return nodes;
};

const JsonView = ({ content }: { content: string }) => {
  try {
    const pretty = JSON.stringify(JSON.parse(content), null, 2);
    return <pre className="font-mono text-3xs leading-relaxed text-muted-foreground">{highlightJson(pretty)}</pre>;
  } catch {
    return <pre className="font-mono text-3xs leading-relaxed whitespace-pre-wrap">{content}</pre>;
  }
};

const InputContent = ({ input, content }: { input: IDemoInput; content: string }) => {
  if (input.name.endsWith('.md')) {
    return (
      <div className="space-y-2 text-xs leading-relaxed [&_h1]:text-sm [&_h1]:font-semibold [&_h1]:tracking-display">
        <Markdown>{content}</Markdown>
      </div>
    );
  }

  if (input.name.endsWith('.csv')) {
    const rows = parseCsv(content);

    if (rows) {
      return <CsvTable rows={rows} />;
    }
  }

  if (input.name.endsWith('.json')) {
    return <JsonView content={content} />;
  }

  return <pre className="font-mono text-3xs leading-relaxed whitespace-pre-wrap">{content}</pre>;
};

interface IIngestBlockProps {
  demo: IDemo;
  droppedFiles: IDroppedFile[] | null;
}

/* Dropped files show their real content; demo cards fall back to the
 * registry excerpts. Rendered by type: markdown, CSV table, JSON. */
const IngestBlock = ({ demo, droppedFiles }: IIngestBlockProps) => {
  const shouldReduceMotion = useReducedMotion();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (name: string): void => {
    setExpanded((current) => ({ ...current, [name]: !current[name] }));
  };

  return (
    <motion.div
      className="space-y-2"
      variants={shouldReduceMotion ? undefined : staggerContainerVariants}
      initial={shouldReduceMotion ? undefined : 'hidden'}
      animate="visible"
    >
      {demo.inputs.map((input) => {
        const dropped = droppedFiles?.find((file) => file.name === input.name);
        const content = dropped?.content ?? input.excerpt;
        const isOpen = !!expanded[input.name];

        return (
          <motion.div
            key={input.name}
            variants={shouldReduceMotion ? undefined : staggerItemVariants}
            className="overflow-hidden rounded-lg border bg-card shadow-soft"
          >
            <button type="button" onClick={() => toggle(input.name)} className="flex w-full items-center gap-2 px-3 py-2 text-left">
              <ChevronRight
                aria-hidden="true"
                className={cn('size-3.5 shrink-0 text-faint-foreground transition-transform', isOpen && 'rotate-90')}
              />
              <span className="truncate font-mono text-xs font-semibold">{input.name}</span>
              <span className="text-2xs text-faint-foreground">{input.description}</span>
              <span className="ml-auto shrink-0 rounded-4xl bg-muted px-2 py-px font-mono text-4xs font-semibold tracking-eyebrow text-muted-foreground uppercase">
                {dropped ? 'dropped' : (KIND_LABELS[input.kind] ?? input.kind)}
              </span>
            </button>
            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  initial={shouldReduceMotion ? undefined : { height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={shouldReduceMotion ? undefined : { height: 0, opacity: 0 }}
                  transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
                  className="overflow-hidden"
                >
                  <ScrollArea className="max-h-48 border-t">
                    <div className="py-2.5 pr-3.5 pl-[34px]">
                      <InputContent input={input} content={content} />
                    </div>
                  </ScrollArea>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}
    </motion.div>
  );
};

export { IngestBlock };
