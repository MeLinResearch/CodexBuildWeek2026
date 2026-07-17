interface IDemoInput {
  name: string;
  kind: 'spec' | 'data' | 'schema';
  description: string;
  excerpt: string;
}

interface IDemo {
  id: string;
  runId: string;
  title: string;
  tagline: string;
  inputs: IDemoInput[];
}

/* The visible product demo is the authoritative core banking fixture served by FastAPI. */
const DEMOS: IDemo[] = [
  {
    id: 'core-banking',
    runId: 'RUN-001',
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
          'record_id,account_id,branch,effective_date,amount,txn_code\nTXN-000001,00012345,101,2026-07-01,1250.00,DEBIT\nTXN-000002,00067890,101,2026-07-01,1200.00,CREDIT\nTXN-000003,00022222,102,not-a-date,0.00,DEBIT\nTXN-000004,00033333,101,2026-07-01,50.00,CREDIT_ADJUSTMENT',
      },
      {
        name: 'target_schema.json',
        kind: 'schema',
        description: 'Shape every migrated record must satisfy',
        excerpt: '{\n  "required": ["account_id", "branch",\n    "effective_date", "amount", "txn_code"],\n  "type": "object"\n}',
      },
    ],
  },
];

const demoByRunId = (runId: string): IDemo | undefined => {
  const canonicalDemo = DEMOS[0];

  if (runId === canonicalDemo.runId) {
    return canonicalDemo;
  }

  if (/^RUN-[0-9]{3}$/.test(runId)) {
    return { ...canonicalDemo, runId };
  }

  return undefined;
};

export type { IDemo, IDemoInput };
export { DEMOS, demoByRunId };
