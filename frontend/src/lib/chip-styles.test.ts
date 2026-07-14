import { describe, expect, it } from 'bun:test';

import { CHIP_STYLES } from '@/lib/chip-styles';

/* Frozen enums from ARCHITECTURE.md §4 and §7. If a value is missing
 * from the chip map it would silently render as a neutral chip, so the
 * map must stay exhaustive over these. */
const ROW_STATUSES = ['pending', 'passed', 'failed', 'patch_pending', 'patch_approved', 'rerun_passed'];
const SEVERITIES = ['blocking', 'warning', 'info'];
const APPROVAL_STATUSES = ['approved', 'rejected'];

describe('status chip enum coverage', () => {
  it('covers every frozen row_status value', () => {
    for (const status of ROW_STATUSES) {
      expect(CHIP_STYLES[status]).toBeDefined();
    }
  });

  it('covers every failure severity', () => {
    for (const severity of SEVERITIES) {
      expect(CHIP_STYLES[severity]).toBeDefined();
    }
  });

  it('covers approval outcomes', () => {
    for (const status of APPROVAL_STATUSES) {
      expect(CHIP_STYLES[status]).toBeDefined();
    }
  });
});
