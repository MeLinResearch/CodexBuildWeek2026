# TypeScript Conventions

## Naming

| Type | Prefix | Example |
|------|--------|---------|
| Types | `T` | `TBugFilter`, `TUserData` |
| Interfaces | `I` | `IProps`, `IUserConfig` |
| Constants | UPPER_CASE | `MAX_RETRY_COUNT` |
| Variables/Functions | camelCase | `calculateTotal` |

## Code Style

- Prefer arrow functions over function declarations
- Avoid domain classes - use functions and hooks instead. `Error` subclasses are an allowed exception (needed for `instanceof` checks); React class-based error boundaries are also allowed (no functional equivalent).
- Use `const` for arrow functions
- Give arrow functions a block body (`() => { ... }`) with an explicit `return` whenever the body chains calls or does more than one thing; a dense single-expression body (e.g. a `getJson(...).then(...)` one-liner) is hard to read. A short, trivial expression body is fine.

```typescript
// Preferred
runEvents: (runId: string): Promise<TRunMessage[]> => {
  return getJson<{ messages: TRunMessage[] }>(`/api/runs/${runId}/events`).then((data) => data.messages);
},

// Avoid
runEvents: (runId: string): Promise<TRunMessage[]> => getJson<{ messages: TRunMessage[] }>(`/api/runs/${runId}/events`).then((data) => data.messages),
```

```typescript
// Preferred
type TBugFilter = "all" | "open" | "closed";

interface IProps {
  userId: string;
}

const calculateTotal = (items: TItem[]): number => {
  return items.reduce((sum, item) => sum + item.price, 0);
};

const MAX_RETRY_COUNT = 3;
```

```typescript
// Avoid
function calculateTotal(items) { ... }

class UserManager { ... }
```
