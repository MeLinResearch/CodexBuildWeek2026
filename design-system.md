## 0. Your task

Build a design system. The product feels like modern serious SaaS — Linear / Vercel.
Calm, precise, editorial-but-technical. **Not** playful, not brutalist, not "AI-gradient slop."

Deliver:

1. A **Tailwind v4 theme** (`@theme` block in CSS with all design tokens as CSS variables).
2. **shadcn/ui** component overrides (`components.json` config + restyled primitives) that match the tokens below.
3. **Base UI** for headless interactive primitives (dropdowns, dialogs, popovers, tabs) styled to match.
4. A **living style guide page** demonstrating every token and component.

Follow the tokens below **exactly** — they are extracted from shipped product code, not invented.

---

## 1. Brand & aesthetic principles

- **Modern serious SaaS.** Restraint over decoration. Every element earns its place.
- **Off-white canvas**, never pure white page background. White is reserved for raised surfaces (cards, app chrome, inputs).
- **One accent only: indigo.** Use it sparingly — for the primary action, active states, citations, and the emphasis gradient. Never flood a surface with it.
- **Monospace is functional chrome only** — citation numbers, judge axes, metadata, counts, keyboard hints, plan labels. **Never** body prose, never headings.
- **No italics, no serif, no decorative fonts.** Emphasis in headings is done with a dark→indigo gradient on the emphasized words (see §3).
- **Hairline borders + soft shadows** define hierarchy, not heavy strokes or big radii.
- Avoid: aggressive gradients as backgrounds, emoji, rounded-corner-with-left-accent-border cards, "data slop" (decorative stats/icons), Inter/Roboto/Arial.

---

## 2. Color tokens

All shipped as hex / rgba. Convert to CSS variables in `@theme`. Provide both a raw palette and semantic aliases.

### Core neutrals

| Token | Value | Use |
|---|---|---|
| `--bg` | `#fafaf9` | Page background (off-white). The default canvas. |
| `--surface` | `#ffffff` | Raised surfaces: cards, app chrome, inputs, dropdowns. |
| `--surface-sunken` | `#f7f6f4` | App title bars, subtle sunken panels. |
| `--surface-muted` | `#f4f3ef` | Chips, tags, tag backgrounds, count pills. |
| `--ink` | `#0a0a0a` | Near-black. Primary text, headings, primary button bg. |
| `--ink-2` | `#1a1a18` | Body prose in article context. |
| `--ink-3` | `#2a2a27` | Quote/secondary body. |
| `--text-secondary` | `#3a3a37` | Nav links, secondary UI text. |
| `--text-muted` | `#4a4a48` | Descriptions, captions. |
| `--text-faint` | `#8a8a85` | Metadata, placeholder, timestamps, section labels. |
| `--text-faintest` | `#c4c4be` / `#d4d4d0` | Separator dots, disabled ticks. |

### Borders (all as rgba over ink)

| Token | Value |
|---|---|
| `--border` | `rgba(10,10,10,.06)` — default hairline (nav, cards, sidebar dividers) |
| `--border-strong` | `rgba(10,10,10,.08)` — buttons/inputs at rest |
| `--border-hover` | `rgba(10,10,10,.12)`–`.18` — hover / emphasis |

### Accent — indigo

| Token | Value | Use |
|---|---|---|
| `--accent` | `#4338ca` | Primary accent. Citations, active nav icon, primary-accent button, links. |
| `--accent-hover` | `#3730a3` | Accent button hover. |
| `--accent-2` | `#6d28d9` | Gradient partner (violet) — used only in the glyph mark & usage bar. |
| `--accent-tint` | `#ecebff` | Accent chip bg (citation source numbers, info badge, pill tag). |
| `--accent-tint-alpha` | `rgba(67,56,202,.08–.20)` | Focus rings, active-cite halo, hover marks. |

### Status

| Token | Value | Paired bg |
|---|---|---|
| Success text | `#047857` | bg `#ecfdf3` |
| Success dot | `#10b981` | — |
| Warning/attn text | `#b45309` | bg `#fef3c7` |
| Warning dot / pulse | `#f59e0b` | ring `rgba(245,158,11,.22)` |
| Danger/problem text | `#be3a1d` | bg `#fef2f0` |

### Gradients (use rarely)

- **Glyph mark:** `linear-gradient(135deg, #4338ca 0%, #6d28d9 100%)`
- **Heading emphasis:** `linear-gradient(180deg, #0a0a0a 0%, #4338ca 100%)` → clipped to text.
- **Usage bar:** `linear-gradient(90deg, #4338ca, #6d28d9)`
- **Hero glow:** `radial-gradient(50% 50% at 50% 50%, rgba(67,56,202,.10) 0%, transparent 70%)`

---

## 3. Typography

**Fonts:** Geist (sans) + Geist Mono. Load weights: Geist 300/400/500/600/700, Geist Mono 400/500/600.
Stack: `'Geist', -apple-system, system-ui, sans-serif` / `'Geist Mono', ui-monospace, monospace`.

**Headings never exceed weight 500.** Emphasis is via the gradient span, not heavier weight or italics.
Tight negative tracking on display sizes.

### Type ramp (from shipped code)

| Role | Size | Weight | Line-height | Letter-spacing |
|---|---|---|---|---|
| Display H1 (hero) | 68px | 500 | 1.04 | -.035em |
| H2 section | 40–48px | 500 | 1.1 | -.03em |
| H2 (article) | 26px | 500 | 1.18 | -.018em |
| H3 / card title | 17–19px | 500 | 1.25 | -.018em |
| Row title (app) | 14.5px | 500 | 1.3 | -.012em |
| Lead / subhead | 19–21px | 400 | 1.5 | — |
| Body prose | 15px | 400 | 1.65 | — |
| UI body | 13–14px | 400/500 | 1.2–1.5 | — |
| Small / meta | 11.5–12.5px | 400/500 | 1.2–1.4 | — |
| Micro (mono labels) | 9.5–11px | 600 | 1.2 | .07–.08em, UPPERCASE |

**Emphasis gradient span** (reusable utility `.grad`):

```css
background: linear-gradient(180deg, #0a0a0a 0%, #4338ca 100%);
-webkit-background-clip: text; background-clip: text; color: transparent;
```

Apply to the 1–2 emphasized words in an H1/H2 — consistently across the whole system.

**Mono usage rule:** section eyebrow labels (UPPERCASE, .07–.08em tracking, `#8a8a85`),
citation numbers, counts, plan/usage figures, timestamps, keyboard hints, judge-axis labels,
tags. Never sentences.

---

## 4. Spacing, radius, shadow

### Radius scale (small — this is a precise product, not a soft one)

| Token | Value | Use |
|---|---|---|
| `--r-xs` | 4px | tags, cite chips, count pills, delta badges |
| `--r-sm` | 6px | badges, glyph mark, nav dots container |
| `--r-md` | 7–8px | buttons, inputs, nav items, source cards |
| `--r-lg` | 12px | content cards (problem, flow steps) |
| `--r-xl` | 14px | app window / hero product mockup |
| `--r-pill` | 999px | pills, chips, status tags, usage bar |

### Spacing rhythm

- Section horizontal padding: **64px** (marketing), **24–32px** (app).
- Card padding: **28px** (marketing feature), **14px** (app source card), **18–24px** (stat cells).
- Grid gaps: **16px** between cards; **32px** nav link gaps; **4–10px** intra-component.
- Nav/topbar vertical padding: **12–18px**.
- Sticky bars use `background: rgba(250,250,249,.85); backdrop-filter: blur(12px)`.

### Shadows (soft, layered, low-opacity ink + faint indigo)

| Token | Value |
|---|---|
| `--shadow-xs` | `0 1px 2px rgba(10,10,10,.04–.06)` — nav items, small raised chips |
| `--shadow-sm` | `0 4px 12px rgba(10,10,10,.04)` — card hover |
| `--shadow-lg` (hero app) | `0 1px 0 rgba(10,10,10,.04), 0 24px 48px -16px rgba(10,10,10,.18), 0 60px 120px -40px rgba(67,56,202,.18)` |
| Focus ring | `0 0 0 3px rgba(67,56,202,.08)` + border `rgba(67,56,202,.4)` |
| Accent button | `0 1px 0 rgba(255,255,255,.2) inset, 0 1px 2px rgba(67,56,202,.4)` |

Transitions: `all .15s` default; `.1s`–`.12s` for nav/hover state changes.

---

## 5. Component patterns (map these to shadcn + Base UI)

### Buttons (`.m-btn` family → shadcn Button variants)

- **primary** — bg `#0a0a0a`, text `#fafaf9`; hover `#2a2a27`.
- **accent** — bg `#4338ca`, text `#fff`, inset+drop shadow above; hover `#3730a3`. (Use for the single most important CTA.)
- **line (outline)** — transparent, `#0a0a0a` text, border `rgba(10,10,10,.12)`; hover bg `rgba(10,10,10,.04)`.
- **ghost** — transparent, `#3a3a37` text; hover `#0a0a0a`.
- Base: font-size 13.5px, weight 500, padding `9px 14px`, radius 8px, line-height 1.2. `lg`: padding `12px 20px`, 14.5px.

### Badges / pills

- **Status badge** (mono, 11.5px, radius 6px): `ok` = green on `#ecfdf3` with a `#10b981` leading dot; `info` = indigo on `#ecebff`.
- **Chip/tag** (mono, 11.5px, radius 4–5px): `#4a4a48` on `#f4f3ef`.
- **Pill** (rounded-full): white bg, hairline border; with inner `--accent-tint` "tag" segment.

### Cards

- Surface `#fff`, border `rgba(10,10,10,.06)`, radius 12px, padding 28px.
- Hover: `box-shadow: 0 4px 12px rgba(10,10,10,.04)` + border darkens to `.1`.
- Source card variant: radius 8px, padding 14px; **active** state = border `rgba(67,56,202,.4)` + focus ring + lift.

### Citation inline chip (signature element)

`.m-cite`: inline-flex, height 18px, padding `0 5px`, radius 4px, mono 11px/600, indigo text on tint bg.
Hover → solid indigo bg, white text. Active → solid + `0 0 0 4px rgba(67,56,202,.18)` halo.

### Stage indicator (pipeline dots — signature app element)

5 stages: `Brief · Research · Draft · Judge · Publish`. Row of **7px** dots, gap 5px.

- default `rgba(10,10,10,.12)`; done/current = `#4338ca`; current adds `0 0 0 2.5px rgba(67,56,202,.2)` halo;
- **attn** = `#f59e0b` + `rgba(245,158,11,.22)` halo + `q-pulse` animation (opacity 1→.55→1 over 2s).
- "attn" table rows get a left 2px amber bar + faint amber gradient wash.

### Judge score pill

mono 11px, rounded-full, leading dot in `currentColor`: green (`#047857`/`#ecfdf3`), amber (`#b45309`/`#fef3c7`), gray (`#6a6a64`/`#f4f3ef`).

### Navigation / sidebar (app shell)

- Sidebar bg `#fafaf9`, right hairline border, sticky full-height.
- Nav item: 13px, `#3a3a37`, radius 7px, transparent border. Hover → `rgba(10,10,10,.04)`.
  **Active** → white bg, `#0a0a0a` text, weight 500, border `rgba(10,10,10,.08)`, `shadow-xs`, and the icon turns indigo.
- Section labels: mono 10px/600 UPPERCASE, .08em, `#8a8a85`.
- Right-aligned count (`.ct`, mono 10.5px faint) or status dot per item.

### Brand mark

22px rounded-6px square, `linear-gradient(135deg,#4338ca,#6d28d9)`, with a small white dot notch top-right ringed in indigo. Wordmark: 15–16px, weight 600, -.015em.

### Inputs

White bg, border `rgba(10,10,10,.08)`, radius 7–8px. Focus → indigo border `.4` + `0 0 0 3px rgba(67,56,202,.08)` ring. Placeholder `#8a8a85`.

### Dialogs / dropdowns / popovers (Base UI, styled)

White surface, radius 12px, `shadow-lg` variant, hairline border. Backdrop = ink at low opacity. Keep them compact and precise.

### Links

Default `--accent` (`#4338ca`); hover `--accent-hover` (`#3730a3`). Always define `a` + `a:hover` even before links exist.

---

## 6. Tailwind v4 + shadcn + Base UI notes

- Put the whole palette + semantic aliases in a single `@theme { --color-*: … }` block so utilities (`bg-bg`, `text-ink`, `border-border`) generate automatically.
- Register the radius, shadow, and font tokens as theme variables too (`--radius-*`, `--shadow-*`, `--font-sans`, `--font-mono`).
- Set shadcn base: `baseColor: neutral`, but override `--background` → `#fafaf9`, `--card`/`--popover` → `#fff`, `--primary` → `#0a0a0a`, `--accent`/`--ring` → `#4338ca`, and small `--radius: .5rem` (8px). Provide a distinct `accent` button variant for the indigo CTA since shadcn's default `--primary` is our black.
- Use **Base UI** for the headless behavior (Dialog, Popover, Menu, Tabs, Tooltip) and apply the surface/shadow/border tokens above; don't pull in a second component library's visual styles.
- Ship dark mode as out-of-scope unless asked — the product is light-only today.

---

## 7. Deliverable: style guide page

Render a single page demonstrating: color swatches (with tokens), the full type ramp with the emphasis gradient, all button variants + states, badges/chips/pills, a card + card-hover, the inline citation chip in a paragraph of body text, the 5-dot stage indicator in every state, the judge score pill trio, and a sidebar nav sample. Label each with its token name.
