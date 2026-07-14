# React Patterns

- Follow the existing app patterns before adding new abstractions.
- Prefer function components and hooks.
- Keep component props typed with `T`/`I` naming conventions from `typescript.md`.
- Use existing UI primitives and styling conventions in `apps/web` before introducing new ones.
- Do not invent a new React architecture for isolated changes.

## Conditional rendering

- For render-or-nothing, use `{cond && <JSX />}`, never `{cond ? <JSX /> : null}`.
- Reserve the ternary for a genuine either/or where both branches render: `{cond ? <A /> : <B />}`.
- The left side of `&&` must be a boolean, so a falsy value never renders itself. Guard non-booleans: write `{list.length > 0 && …}` and `{value != null && …}`, or coerce with `!!value`. Never `{list.length && …}` or `{count && …}` (renders a stray `0`), and never a bare string (renders `''`).
