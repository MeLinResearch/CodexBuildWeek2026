import type { TFailure } from '@/api/client';

interface IFailureMeta {
  title: string;
  meaning: string;
  requirementText: string;
}

const CANONICAL_FAILURE_META: readonly IFailureMeta[] = [
  {
    title: 'Leading zeros stripped',
    meaning: 'Account IDs were coerced to integers during migration, silently dropping leading zeros.',
    requirementText: 'Preserve account identifiers verbatim',
  },
  {
    title: 'Branch 101 out of balance',
    meaning: 'One transaction code flips its sign, so global totals pass while Branch 101 does not.',
    requirementText: 'Debits equal credits by branch',
  },
  {
    title: 'Silent date default',
    meaning: 'Unparseable dates were coerced to 1900-01-01 instead of being rejected.',
    requirementText: 'No silent value substitution',
  },
];

const failureMeta = (requirementId: string, failure?: TFailure): IFailureMeta => {
  const match = /^REQ-(\d{3})$/.exec(requirementId);
  const requirementNumber = match ? Number(match[1]) : 0;

  if (requirementNumber >= 1) {
    return CANONICAL_FAILURE_META[(requirementNumber - 1) % CANONICAL_FAILURE_META.length];
  }

  return {
    title: failure?.field ?? requirementId,
    meaning: failure?.expected ?? 'See the failed record for details.',
    requirementText: requirementId,
  };
};

export { failureMeta };
