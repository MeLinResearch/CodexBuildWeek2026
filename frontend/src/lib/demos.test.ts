import { readFile } from 'node:fs/promises';

import { describe, expect, test } from 'bun:test';

import { DEMOS } from '@/lib/demos';

const EXPECTED_ACCOUNTS_CSV = [
  'record_id,account_id,branch,effective_date,amount,txn_code',
  'TXN-000001,00012345,101,2026-07-01,1250.00,DEBIT',
  'TXN-000002,00067890,101,2026-07-01,1200.00,CREDIT',
  'TXN-000003,00022222,102,not-a-date,0.00,DEBIT',
  'TXN-000004,00033333,101,2026-07-01,50.00,CREDIT_ADJUSTMENT',
].join('\n');

describe('core banking demo inputs', () => {
  test('displayed, downloadable, and canonical source data stay identical', async () => {
    const demo = DEMOS.find(({ id }) => id === 'core-banking');
    const dataInput = demo?.inputs.find(({ name }) => name === 'accounts.csv');

    const publicCsv = await readFile(
      new URL('../../public/demo-inputs/core-banking/accounts.csv', import.meta.url),
      'utf8',
    );
    const canonicalCsv = await readFile(
      new URL('../../../fixtures/source_data/accounts.csv', import.meta.url),
      'utf8',
    );

    expect(dataInput?.excerpt).toBe(EXPECTED_ACCOUNTS_CSV);
    expect(publicCsv.trimEnd()).toBe(EXPECTED_ACCOUNTS_CSV);
    expect(canonicalCsv.trimEnd()).toBe(EXPECTED_ACCOUNTS_CSV);
  });
});
