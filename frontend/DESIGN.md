---
version: beta
name: internal-exam-platform-academic-editorial
updated: 2026-06-14
description: Academic Editorial design system for the internal exam platform frontend.
---

# Frontend Design

The frontend uses an Academic Editorial style: quiet white and warm paper surfaces, black ink typography, restrained borders, pill controls, and dense but readable exam/admin workflows. The product should feel like an internal assessment desk, not a marketing site.

## Source Files

- `src/index.css`: CSS variables, base typography, focus ring, shimmer utility.
- `tailwind.config.ts`: Tailwind aliases for color, radius, font, shadow, and type scale.
- `src/lib/design-tokens.ts`: TypeScript mirror for rare runtime/raw-token needs.
- `src/components/ui/`: local shadcn-compatible primitives.
- `src/components/editorial/`: product-specific editorial components.
- `src/components/layout/`: candidate/admin shells and navigation.

## Tokens

Surfaces:

- `--canvas`: `#ffffff`
- `--canvas-warm`: `#fafaf7`
- `--surface-card`: `#f5f3ee`
- `--surface-elev`: `#ffffff`

Text and lines:

- `--ink`: `#111111`
- `--ink-soft`: `#2a2a2a`
- `--body`: `#374151`
- `--muted`: `#6b7280`
- `--hairline`: `#e5e7eb`
- `--hairline-soft`: `#f3f4f6`

Status:

- `--success`: `#166534`
- `--warning`: `#b45309`
- `--error`: `#b91c1c`

Shape and depth:

- radius: pill `9999px`, lg `16px`, md `8px`, sm `4px`
- shadows: `shadow-card`, `shadow-pop`, `shadow-elevate`

Do not reintroduce old `hsl(var(--...))` shadcn tokens. Use Tailwind aliases such as `bg-canvas`, `bg-canvas-warm`, `bg-surface-card`, `text-ink`, `text-body`, `text-muted`, `border-hairline`, and semantic status colors.

## Typography

- Display: `Manrope`, used for page and section headings.
- Body: `Inter`, used for UI, prose, form controls, and table text.
- Mono: `JetBrains Mono`, used for counters, codes, and tabular identifiers.

Display headings intentionally use slight negative letter spacing through the configured type scale. Body text should stay at normal letter spacing.

## Component Rules

- Reuse local UI primitives from `src/components/ui/` before adding a new primitive.
- Reuse editorial components such as `ChapterNumber`, `NamePlate`, `Wordmark`, `StatusPill`, `EmptyState`, and `ContentSkeleton` for repeated product states.
- Keep frontend API calls in `src/api/`; pages should compose hooks, API clients, and components rather than hand-writing fetch logic.
- For admin tables, prefer `SimpleDataTable` and its mobile card renderer instead of creating separate mobile-only lists.
- For metric summaries, use `MetricCard` so tone, label, value, unit, and caption styling stay consistent.

## Layouts

Candidate pages use `CandidateLayout` with top navigation, footer, warm editorial surfaces, and exam-focused content bands. Exam-taking uses focus mode, question navigation, answer cards, timer state, and keyboard shortcuts.

Admin pages use `AdminLayout` with side rail navigation, compact page headers, metric rows, table/report sections, and mobile fallbacks. Admin screens should remain operational and scan-friendly, with no marketing hero sections.

## States

- Empty/error states: use `EmptyState`; set `tone="error"` for recoverable page-level errors.
- Loading states: use `ContentSkeleton`, which exposes `role="status"` and `aria-busy`.
- Timer urgency: `Timer` switches to `text-error` and pulse when the remaining time is at or below 5 minutes.
- Keyboard shortcuts on the exam page: `ArrowLeft` / `ArrowRight` change questions; `1-9` and `A-D` select options. Inputs, textareas, and contenteditable elements must not be intercepted.

## Accessibility

- Keep visible focus rings from `:focus-visible`.
- Icon-only buttons must have accessible labels.
- Dialog and Sheet usage should include titles/descriptions or explicit Radix-compliant alternatives.
- Option cards expose radio/checkbox semantics according to question type.
- Mobile question navigation uses a Sheet rather than hidden off-screen controls.

## Verification

For frontend-affecting changes, run:

```bash
cd frontend
npm test
npx tsc --noEmit
npm run lint
npm run format:check
npm run build
```

Known non-blocking lint warnings remain in `src/components/ui/badge.tsx` and `src/components/ui/button.tsx` from `react-refresh/only-export-components`.
