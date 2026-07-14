# Code Style

## Formatting

- Biome handles formatting - run `bun run lint` to check
- NEVER add comments directly before an `if` statement (Biome may break code)
- ALWAYS use full block form for conditionals, never single-line returns (enforced by Biome's `useBlockStatements`):

```ts
// Incorrect
if (ok) return value;

// Correct
if (ok) {
  return value;
}
```

## File Naming

ALWAYS use kebab-case: `user-profile.tsx`, `api-service.ts`

NEVER use: `UserProfile.tsx`, `user_profile.tsx`, `userProfile.tsx`

## Ref Naming

Use `ref{Name}` prefix format:

```tsx
const refContainer = useRef<HTMLDivElement>(null);
const refInputElement = useRef<HTMLInputElement>(null);

// Incorrect - never use suffix
const containerRef = useRef();
```

## Comments

- NEVER write comments that restate what the code does
- NEVER add bare separator lines (`// ===...` or `// ---...`) without a meaningful section label
- Only comment WHY something is done when the reason isn't obvious from context
- Exception: `// HACK: reason` for known workarounds

## Git Commits

- NEVER add `Co-Authored-By` to commit messages
