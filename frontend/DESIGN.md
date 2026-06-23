---
version: beta
name: internal-exam-platform-academic-editorial
updated: 2026-06-16
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

- Display: `Source Serif 4` (with `Songti SC` / `Noto Serif SC` fallback for Chinese characters). Used for page and section headings — gives the product an academic, paper-grade feel that matches the "知试" brand voice.
- Body: `Inter` (with `PingFang SC` / `Hiragino Sans GB` for CJK). Used for UI, prose, form controls, and table text.
- Mono: `JetBrains Mono`, used for counters, codes, and tabular identifiers.

Display headings use modest negative letter spacing (`-0.01em` / `-0.02em`) through the configured type scale — serif italics at heavy negative tracking collapse glyphs. Body text should stay at normal letter spacing.

### H1 rules

- Page-level H1 must use `font-display text-display-lg lg:text-display-xl font-semibold text-ink` (do not specify raw `text-[Npx]`).
- H1 stays upright by default. Italic is reserved for *emphasis phrases* inside an H1 (wrap with `<em class="italic">…</em>`) and for the `ChapterNumber` marginalia.
- `EmptyState` H2 also stays upright; use `<em class="italic">…</em>` for emphasis.

## Component Rules

- Reuse local UI primitives from `src/components/ui/` before adding a new primitive.
- Reuse editorial components such as `ChapterNumber`, `NamePlate`, `Wordmark`, `StatusPill`, `EmptyState`, and `ContentSkeleton` for repeated product states.
- Keep frontend API calls in `src/api/`; pages should compose hooks, API clients, and components rather than hand-writing fetch logic.
- For admin tables, prefer `SimpleDataTable` and its mobile card renderer instead of creating separate mobile-only lists.
- For metric summaries, use `MetricCard` so tone, label, value, unit, and caption styling stay consistent.

## Neutral chip & surface rule

`StatusPill` default and `Badge` muted share the same neutral surface (`bg-canvas-warm`). If you need a different neutral (e.g. on a dark card), use a surface-specific variant rather than introducing a new shade.

## Radius rule

- Display cards (Card, ExamFocusMode article, TopRankCard, ExamCard) → `rounded-lg` (16px).
- Information-dense surfaces (Table, DataCard, Input, Select, Textarea) → `rounded-md` (8px).
- Pills, capsules, navigation, buttons → `rounded-pill` (full).
- Chips / badges / status pills → `rounded-sm` (4px).

## Sticky header pattern

Use the shared `useScrolled` hook to toggle `data-scrolled` on the sticky header. The `[data-scrolled="true"]` selector in `index.css` applies a hairline shadow so the header has a visual anchor once the user has scrolled.

## Stagger entrance

Add `data-stagger` to a top-level page container to opt into the editorial entrance keyframe. Children rise in quickly from 72% opacity with a 40ms delay step, so mobile first paint remains readable instead of briefly washing out. The animation respects `prefers-reduced-motion`.

## Layouts

Candidate pages use `CandidateLayout` with top navigation, footer, warm editorial surfaces, and exam-focused content bands. The `/login` route is the exception: it keeps the candidate session context but renders as a clean auth canvas without candidate navigation or footer. Exam-taking uses focus mode, question navigation, answer cards, timer state, and keyboard shortcuts.

Candidate and admin page-level eyebrow copy is centralized in `src/lib/pageCopy.ts`. Use descriptive labels such as `PRACTICE · 练习`, `OVERVIEW · 仪表盘`, `REPORTS · 报表`, and `STATE · 空状态` for pages and states. Page-level labels must not use fictional chapter numbers; reserve numbered `QUESTION NN · 类型 · 分值` labels for real question position inside the taking/practice focus card.

Admin pages use `AdminLayout` with side rail navigation, compact page headers, metric rows, table/report sections, and mobile fallbacks. Admin screens should remain operational and scan-friendly, with no marketing hero sections.

## States

- Empty/error states: use `EmptyState`; set `tone="error"` for recoverable page-level errors.
- Loading states: use `ContentSkeleton`, which exposes `role="status"` and `aria-busy`.
- Timer urgency: `Timer` switches to `text-error` and pulse when the remaining time is at or below 5 minutes.
- Keyboard shortcuts on the exam page: `ArrowLeft` / `ArrowRight` change questions; `1-9` and `A-D` select options. Inputs, textareas, and contenteditable elements must not be intercepted.
- Exam-taking primary action: earlier questions show “下一题”; the final question shows “提交试卷” and calls the normal manual submit flow.

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
