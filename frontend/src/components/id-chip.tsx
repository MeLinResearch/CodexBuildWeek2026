import { cn } from '@/lib/utils';

type TIdTone = 'req' | 'test' | 'fail';

const TONE_STYLES: Record<TIdTone, string> = {
  req: 'bg-accent text-accent-foreground',
  test: 'bg-info-soft text-info',
  fail: 'bg-destructive-soft text-destructive',
};

interface IIdChipProps {
  id: string;
  tone: TIdTone;
  className?: string;
}

/* One chip family for the stable IDs (REQ / TEST / FAIL), so every
 * list and table renders them identically; only the hue changes. */
const IdChip = ({ id, tone, className }: IIdChipProps) => {
  return (
    <span className={cn('inline-flex rounded-md px-2 py-0.5 font-mono text-3xs font-semibold whitespace-nowrap', TONE_STYLES[tone], className)}>
      {id}
    </span>
  );
};

export { IdChip };
