import { CHIP_DOTS, CHIP_STYLES } from '@/lib/chip-styles';
import { cn } from '@/lib/utils';

interface IStatusChipProps {
  status: string;
  className?: string;
}

const StatusChip = ({ status, className }: IStatusChipProps) => {
  const style = CHIP_STYLES[status] ?? 'bg-muted text-muted-foreground';
  const dot = CHIP_DOTS[status];

  return (
    <span
      className={cn(
        'inline-flex h-5 w-fit shrink-0 items-center gap-1.5 whitespace-nowrap rounded-4xl px-2 font-mono text-3xs font-semibold tracking-eyebrow',
        style,
        className,
      )}
    >
      {!!dot && <span aria-hidden="true" className={cn('size-1.5 rounded-full', dot)} />}
      {status.replaceAll('_', ' ')}
    </span>
  );
};

export { StatusChip };
