/* Chip styling for the frozen row_status enum (ARCHITECTURE.md §4)
 * plus the shared statuses (severity, patch, approval) that reuse the
 * same visual language. Unknown values render neutral rather than
 * inventing a state. */
const CHIP_STYLES: Record<string, string> = {
  pending: 'bg-muted text-muted-foreground',
  passed: 'bg-success-soft text-success',
  failed: 'bg-destructive-soft text-destructive',
  patch_pending: 'bg-warning-soft text-warning',
  patch_approved: 'bg-accent text-accent-foreground',
  rerun_passed: 'bg-success-soft text-success',
  blocking: 'bg-destructive-soft text-destructive',
  warning: 'bg-warning-soft text-warning',
  info: 'bg-accent text-accent-foreground',
  approved: 'bg-success-soft text-success',
  rejected: 'bg-destructive-soft text-destructive',
};

const CHIP_DOTS: Record<string, string> = {
  patch_pending: 'bg-warning-indicator animate-attn-pulse',
  rerun_passed: 'bg-success-indicator',
  passed: 'bg-success-indicator',
};

export { CHIP_DOTS, CHIP_STYLES };
