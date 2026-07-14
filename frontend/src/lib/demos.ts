interface IDemoInput {
  name: string;
  kind: 'spec' | 'data' | 'schema';
  description: string;
  excerpt: string;
}

interface IDemo {
  id: string;
  runId: string;
  patchId: string;
  title: string;
  tagline: string;
  inputs: IDemoInput[];
}

/* Demo 1 excerpts are verbatim from the repo's fixture inputs
 * (fixtures/implementation_doc.md, source_data/accounts.csv,
 * schemas/target_schema.json). Demos 2 and 3 are authored fixture
 * sets; their excerpts are demo copy consistent with their mocks. */
const DEMOS: IDemo[] = [
  {
    id: 'core-banking',
    runId: 'RUN-001',
    patchId: 'PATCH-001',
    title: 'Core banking migration',
    tagline: 'Account IDs, branch balancing, date hygiene',
    inputs: [
      {
        name: 'implementation_doc.md',
        kind: 'spec',
        description: 'Conversion spec, source of the requirements',
        excerpt:
          '# Bank Migration Demo Implementation Doc\n\nRequirements: preserve account identifiers verbatim; debits equal credits by branch; no silent value substitution.',
      },
      {
        name: 'accounts.csv',
        kind: 'data',
        description: 'Source ledger records',
        excerpt:
          'record_id,account_id,branch,effective_date,amount,txn_code\nTXN-000001,00012345,101,2026-07-01,1250.00,DEBIT\nTXN-000002,00067890,101,2026-07-01,1200.00,CREDIT\nTXN-000003,00022222,101,not-a-date,50.00,DEBIT',
      },
      {
        name: 'target_schema.json',
        kind: 'schema',
        description: 'Shape every migrated record must satisfy',
        excerpt: '{\n  "required": ["account_id", "branch",\n    "effective_date", "amount", "txn_code"],\n  "type": "object"\n}',
      },
    ],
  },
  {
    id: 'card-portfolio',
    runId: 'RUN-002',
    patchId: 'PATCH-002',
    title: 'Card portfolio conversion',
    tagline: 'Tier mapping, interest rounding, currency codes',
    inputs: [
      {
        name: 'card_conversion_spec.md',
        kind: 'spec',
        description: 'Product mapping and tolerance rules',
        excerpt:
          '# Card Portfolio Conversion Spec\n\nRequirements: map legacy product codes to the new tier scheme; recomputed interest within 0.01; currency codes are valid ISO 4217.',
      },
      {
        name: 'cards.csv',
        kind: 'data',
        description: 'Card master records',
        excerpt:
          'record_id,product_code,product_tier,accrued_interest,currency\nCARD-004417,GR-441,GOLD_REWARDS,12.40,GBP\nCARD-002906,ST-290,STANDARD,41.87,GBP\nCARD-009152,PL-915,PLATINUM,88.02,UKP',
      },
      {
        name: 'card_schema.json',
        kind: 'schema',
        description: 'Target card record shape',
        excerpt: '{\n  "required": ["product_tier",\n    "accrued_interest", "currency"],\n  "type": "object"\n}',
      },
    ],
  },
  {
    id: 'loan-book',
    runId: 'RUN-003',
    patchId: 'PATCH-003',
    title: 'Loan book cutover',
    tagline: 'Schedule dates, accrual precision, borrower dedupe',
    inputs: [
      {
        name: 'loan_cutover_spec.md',
        kind: 'spec',
        description: 'Cutover rules for schedules and balances',
        excerpt:
          '# Loan Book Cutover Spec\n\nRequirements: payment schedule dates survive timezone conversion; accrued interest carries to the cent; borrower identifiers stay unique after merge.',
      },
      {
        name: 'loans.csv',
        kind: 'data',
        description: 'Loan master records',
        excerpt:
          'record_id,borrower_id,next_payment_date,accrued_interest\nLOAN-001208,BWR-0089,2026-03-01,301.55\nLOAN-004551,BWR-0412,2026-03-15,1204.66\nLOAN-007823,BWR-1102,2026-04-01,77.14',
      },
      {
        name: 'loan_schema.json',
        kind: 'schema',
        description: 'Target loan record shape',
        excerpt: '{\n  "required": ["borrower_id",\n    "next_payment_date", "accrued_interest"],\n  "type": "object"\n}',
      },
    ],
  },
];

const demoByRunId = (runId: string): IDemo | undefined => {
  return DEMOS.find((demo) => demo.runId === runId);
};

export type { IDemo, IDemoInput };
export { DEMOS, demoByRunId };
