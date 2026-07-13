# Agent Instructions

Read these shared instruction files:

- [Collaboration & Mindset](.agents/instructions/collaboration.md)
- [Code Style](.agents/instructions/code-style.md)
- [TypeScript](.agents/instructions/typescript.md)
- [React Patterns](.agents/instructions/react.md)

## Checks

Requires Node >= 22 (see `.nvmrc`; the shell loads it via `nvm use`).

After changing code, run a single command:

```bash
bun lint
```

It runs Biome, the TypeScript typecheck, and knip together. Do not run the three separately. Run `bun test` for the test suite.
