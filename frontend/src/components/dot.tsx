import { cn } from '@/lib/utils';

interface IDotProps {
  /* Multiples of 4px; size 1 = 4px. */
  size?: number;
  className?: string;
}

/* Separator/status dot. Inherits color from the surrounding text via
 * bg-current; pass a text-* or bg-* class to override. */
const Dot = ({ size = 1, className }: IDotProps) => {
  return (
    <span
      aria-hidden="true"
      style={{ width: size * 4, height: size * 4 }}
      className={cn('inline-block shrink-0 rounded-full bg-current opacity-60', className)}
    />
  );
};

export { Dot };
