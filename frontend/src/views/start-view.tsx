import { useNavigate } from '@tanstack/react-router';
import { Check, FileUp, Play } from 'lucide-react';
import { motion, useReducedMotion, type Variants } from 'motion/react';
import { type DragEvent, useState } from 'react';

import { DEMOS, type IDemo } from '@/lib/demos';
import { cn } from '@/lib/utils';
import { fadeInUpVariants } from '@/lib/variants';
import { type IDroppedFile, useRunUi } from '@/state/run-store';

/* Dropped files select the demo set they belong to by filename. When
 * the live pipeline lands, this same handler posts them to /api/runs
 * instead of matching locally. */
const matchDemo = (fileNames: string[]): IDemo | undefined => {
  let best: { demo: IDemo; hits: number } | undefined;

  for (const demo of DEMOS) {
    const hits = demo.inputs.filter((input) => fileNames.includes(input.name)).length;

    if (hits > 0 && hits > (best?.hits ?? 0)) {
      best = { demo, hits };
    }
  }

  return best?.demo;
};

/* The demo cards rise further and stagger slower than the shared
 * timeline variants; with only three of them the sequence reads as
 * intentional instead of a glitchy near-simultaneous fade. The
 * container only orchestrates: fading it too would compound with the
 * children's own opacity ramp. */
const cardContainerVariants: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.18, delayChildren: 0.15 },
  },
};

const cardItemVariants: Variants = {
  hidden: { opacity: 0, y: 32 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] },
  },
};

/* What this demo is, readable in two seconds: deterministic, fixture
 * mode, nothing sensitive leaves the machine. */
const DEMO_FACTS = ['Deterministic fixture replay', 'No live data, no secrets', 'Validated against frozen contracts'];

const readFiles = async (files: File[]): Promise<IDroppedFile[]> => {
  return Promise.all(
    files.map(async (file) => {
      return { name: file.name, content: await file.text() };
    }),
  );
};

const StartView = () => {
  const shouldReduceMotion = useReducedMotion();
  const navigate = useNavigate();
  const { beginRun } = useRunUi();
  const [dragging, setDragging] = useState(false);
  const [dropError, setDropError] = useState<string | null>(null);

  const handleDrop = async (event: DragEvent<HTMLDivElement>): Promise<void> => {
    event.preventDefault();
    setDragging(false);

    const files = [...event.dataTransfer.files];
    const demo = matchDemo(files.map((file) => file.name));

    if (!demo) {
      setDropError('These files do not match a demo input set. Live mode will accept arbitrary inputs once the pipeline lands.');
      return;
    }

    setDropError(null);
    beginRun(await readFiles(files));
    navigate({ to: '/$runId', params: { runId: demo.runId } });
  };

  return (
    <div className="mx-auto w-full max-w-[880px]">
      <motion.div
        variants={shouldReduceMotion ? undefined : fadeInUpVariants}
        initial={shouldReduceMotion ? undefined : 'hidden'}
        animate="visible"
        className="pt-6 pb-8 text-center"
      >
        <div className="eyebrow">Release assurance for bank migrations</div>
        <h1 className="mx-auto mt-2 text-[34px] leading-[1.15] font-medium tracking-display text-balance">
          Every migrated record, <span className="grad">proven and gated</span>
        </h1>
        <p className="mx-auto mt-3 max-w-[540px] text-sm leading-relaxed text-muted-foreground">
          The spec becomes executable tests. Every failure maps back to a requirement. Codex proposes the fix, and nothing ships without your
          approval.
        </p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          {DEMO_FACTS.map((fact) => (
            <span
              key={fact}
              className="inline-flex items-center gap-1.5 rounded-4xl border bg-card/60 px-3 py-1 text-2xs font-medium text-muted-foreground"
            >
              <Check aria-hidden="true" className="size-3 text-success" />
              {fact}
            </span>
          ))}
        </div>
      </motion.div>

      <motion.div variants={shouldReduceMotion ? undefined : fadeInUpVariants} initial={shouldReduceMotion ? undefined : 'hidden'} animate="visible">
        <section
          aria-label="Drop demo input files"
          onDragOver={(event: DragEvent<HTMLDivElement>) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={cn(
            'flex flex-col items-center gap-1.5 rounded-xl border border-dashed bg-card/60 px-6 py-8 text-center transition-all',
            dragging ? 'border-primary/50 bg-accent/40 shadow-lift' : 'border-input',
          )}
        >
          <FileUp aria-hidden="true" className={cn('size-6', dragging ? 'text-primary dark:text-primary-subtle' : 'text-faint-foreground')} />
          <p className="text-sm font-medium">Drop a conversion spec, source data, and target schema</p>
          <p className="text-2xs text-faint-foreground">
            Fixture mode recognizes the demo input sets below. Live mode will send your files to the pipeline.
          </p>
          {!!dropError && <p className="mt-1 max-w-[440px] text-2xs text-warning">{dropError}</p>}
        </section>
      </motion.div>

      <motion.div
        className="mt-8 grid gap-4 lg:grid-cols-3"
        variants={shouldReduceMotion ? undefined : cardContainerVariants}
        initial={shouldReduceMotion ? undefined : 'hidden'}
        animate="visible"
      >
        {DEMOS.map((demo) => (
          <motion.button
            key={demo.id}
            type="button"
            variants={shouldReduceMotion ? undefined : cardItemVariants}
            onClick={() => {
              beginRun();
              navigate({ to: '/$runId', params: { runId: demo.runId } });
            }}
            className="group flex flex-col rounded-xl border bg-card p-5 text-left transition-[border-color,box-shadow] duration-200 hover:border-primary/35 hover:shadow-lift"
          >
            <span className="font-mono text-3xs font-semibold tracking-eyebrow text-faint-foreground uppercase">{demo.runId}</span>
            <span className="mt-1.5 text-[15px] font-medium tracking-display">{demo.title}</span>
            <span className="mt-0.5 flex-1 text-2xs font-medium text-primary dark:text-primary-subtle">{demo.tagline}</span>
            <span className="mt-4 flex flex-col gap-1.5">
              {demo.inputs.map((input) => (
                <span key={input.name} className="flex items-center gap-2 font-mono text-4xs text-muted-foreground">
                  <span aria-hidden="true" className="size-1.5 shrink-0 rounded-full bg-primary/70 dark:bg-primary-subtle/70" />
                  {input.name}
                </span>
              ))}
            </span>
            <span className="mt-4 inline-flex w-fit items-center gap-1.5 rounded-full bg-primary px-4 py-1.5 text-xs font-medium text-primary-foreground shadow-soft transition-[background-color,box-shadow] duration-200 group-hover:bg-primary/90 group-hover:shadow-lift">
              <Play aria-hidden="true" className="size-3 fill-current" />
              Run the demo
            </span>
          </motion.button>
        ))}
      </motion.div>
    </div>
  );
};

export { StartView };
