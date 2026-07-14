import type { TFailure } from '@/api/client';

/* Presentation copy for the three planted defects (DEFECTS.md). Keyed
 * by requirement_id per the design spec; unknown requirements fall
 * back to the record's own expected text. */
interface IFailureMeta {
  title: string;
  meaning: string;
  requirementText: string;
}

const FAILURE_META: Record<string, IFailureMeta> = {
  'REQ-001': {
    title: 'Leading zeros stripped',
    meaning: 'Account IDs were coerced to integers during migration, silently dropping leading zeros.',
    requirementText: 'Preserve account identifiers verbatim',
  },
  'REQ-002': {
    title: 'Branch 101 out of balance',
    meaning: 'One transaction code flips its sign, so global totals pass while Branch 101 does not.',
    requirementText: 'Debits equal credits by branch',
  },
  'REQ-003': {
    title: 'Silent date default',
    meaning: 'Unparseable dates were coerced to 1900-01-01 instead of being rejected.',
    requirementText: 'No silent value substitution',
  },
  'REQ-004': {
    title: 'Tier mapped to STANDARD',
    meaning: 'Unknown legacy product codes fell back to STANDARD instead of failing the mapping.',
    requirementText: 'Map legacy product codes to the new tier scheme',
  },
  'REQ-005': {
    title: 'Interest drifts past tolerance',
    meaning: 'Float rounding recomputed interest 0.03 away from the source, past the 0.01 tolerance.',
    requirementText: 'Recomputed interest within 0.01 of source',
  },
  'REQ-006': {
    title: 'Unknown currency passed through',
    meaning: 'The legacy alias UKP was migrated verbatim instead of normalizing to ISO 4217 GBP.',
    requirementText: 'Currency codes are valid ISO 4217',
  },
  'REQ-007': {
    title: 'Payment date shifted a day',
    meaning: 'Timezone conversion moved a civil schedule date across midnight to the previous day.',
    requirementText: 'Payment schedule dates survive timezone conversion',
  },
  'REQ-008': {
    title: 'Accrual lost precision',
    meaning: 'Accrued interest went through a float and lost half a cent on the way in.',
    requirementText: 'Accrued interest carries to the cent',
  },
  'REQ-009': {
    title: 'Duplicate borrower survived',
    meaning: 'The dedupe merge let the same borrower id through twice instead of raising.',
    requirementText: 'Borrower identifiers stay unique after merge',
  },
  'REQ-010': {
    title: 'Principal balances reconcile',
    meaning: 'Every migrated principal balance matched the source ledger to the cent.',
    requirementText: 'Principal balances reconcile to the source ledger',
  },
};

const failureMeta = (requirementId: string, failure?: TFailure): IFailureMeta => {
  const meta = FAILURE_META[requirementId];

  if (meta) {
    return meta;
  }

  return {
    title: failure?.field ?? requirementId,
    meaning: failure?.expected ?? 'See the failed record for details.',
    requirementText: requirementId,
  };
};

export { failureMeta };
