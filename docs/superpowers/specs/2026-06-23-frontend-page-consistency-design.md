# Candidate And Admin Page Consistency Design

## Summary

Unify candidate-facing and admin-facing pages under one shared Academic Editorial page structure while preserving their different navigation models and business workflows.

The implementation should follow **shared page skeleton + per-area layout adapters**:

- Candidate pages keep top navigation through `CandidateLayout`.
- Admin pages keep side rail navigation through `AdminLayout`.
- Both areas use shared page primitives for headers, sections, state surfaces, and page-level spacing.
- Exam-taking and practice focus mode are included in the consistency audit, but remain specialized flows rather than being forced into a generic page shell.

This is a design-system consolidation, not a product redesign.

## Goals

1. Make ordinary candidate and admin pages feel like they belong to the same product.
2. Reduce duplicated page-level structure such as header markup, page spacing, section cards, loading states, empty states, and error states.
3. Keep admin pages dense and operational, while keeping candidate pages calm and exam-focused.
4. Preserve the current Academic Editorial visual language defined in `frontend/DESIGN.md`.
5. Make future page additions harder to drift away from the system.

## Non-Goals

- Do not replace candidate top navigation with admin side navigation.
- Do not replace admin side rail with candidate top navigation.
- Do not redesign the brand, color palette, typography, or token system.
- Do not change backend APIs, auth flows, exam scoring, import behavior, or report semantics.
- Do not force exam-taking and practice focus mode into the same layout as ordinary list/report pages.
- Do not introduce a new component library or reset shadcn-compatible primitives.

## Current Context

The frontend already uses an Academic Editorial design system:

- Tokens and Tailwind aliases live in `frontend/src/index.css` and `frontend/tailwind.config.ts`.
- Product-specific primitives live in `frontend/src/components/editorial/`.
- Layouts live in `frontend/src/components/layout/`.
- Page-level microcopy is centralized in `frontend/src/lib/pageCopy.ts`.
- Candidate pages use `CandidateLayout` and top navigation.
- Admin pages use `AdminLayout` and `AdminSideRail`.
- Admin report/table pages already share `ReportPage`.

Recent work unified page-level eyebrow copy. The next drift risk is structural: ordinary pages still repeat headers, surfaces, spacing, and states by hand.

## Design Direction

### 1. Shared Page Primitives

Add a small set of shared components under `frontend/src/components/page/`.

Proposed components:

- `PageShell`
- `PageHeader`
- `PageSection`
- `PageState`
- `PageActions`

These components should use existing tokens and existing editorial primitives. They should not invent a new visual language.

### 2. PageShell

`PageShell` defines the outer page rhythm:

- top-level vertical spacing
- optional max width
- optional stagger entrance
- density mode

Suggested API shape:

```tsx
<PageShell density="calm" data-stagger>
  {children}
</PageShell>
```

Density modes:

- `calm`: candidate ordinary pages, login-adjacent content, exam explanation
- `workbench`: admin pages and report/table workflows
- `focus`: exam-taking and practice pages where the shell only controls broad spacing

Candidate ordinary pages should mostly use `calm`.
Admin pages should mostly use `workbench`.
Exam-taking and practice should use `focus` sparingly or only for outer rhythm.

### 3. PageHeader

`PageHeader` standardizes page-level eyebrow, H1, description, and actions.

Suggested API shape:

```tsx
<PageHeader
  eyebrow={candidatePageCopy.exams}
  title="可参加考试"
  description="选择一场考试，开始前请确认考试规则。"
  actions={<Button>刷新</Button>}
/>
```

Rules:

- Eyebrow always uses `ChapterNumber`.
- Page H1 always follows the `frontend/DESIGN.md` H1 rule:
  `font-display text-display-lg lg:text-display-xl font-semibold text-ink`.
- Actions sit beside the title on wider screens and stack below on mobile.
- Long actions must wrap cleanly and must not resize the header unexpectedly.
- Page-level labels must come from `candidatePageCopy` or `adminPageCopy` where applicable.

### 4. PageSection

`PageSection` standardizes repeated content surfaces.

Suggested variants:

- `plain`: unframed page band or grouping
- `card`: display card surface, `rounded-lg`, `border-hairline`, `shadow-card`
- `panel`: information-dense surface, `rounded-md`, compact padding
- `table`: table/report wrapper, aligned with `SimpleDataTable`

Candidate pages should use `card` for exam cards and result review groups.
Admin pages should use `panel` or `table` for dense work surfaces.

This keeps both sides consistent without making admin pages feel too spacious or candidate pages too mechanical.

### 5. PageState

`PageState` wraps existing `EmptyState` and `ContentSkeleton` patterns into a page-level contract.

Supported states:

- `loading`
- `empty`
- `error`
- `notLoggedIn`
- `notStarted`
- `submitted`

It should delegate visuals to existing editorial components rather than replace them.

Example:

```tsx
<PageState
  state="empty"
  eyebrow={adminPageCopy.empty}
  title="暂无活动记录。"
  description="当有人交卷或缺席名单产生后，最近活动会显示在这里。"
/>
```

This reduces the chance that one side uses a bare skeleton while the other uses a polished state card.

### 6. Candidate Pages

Candidate ordinary pages should migrate to the shared primitives:

- `LoginPage`
- `ExamListPage`
- `ExamStartPage`
- `ExamResultPage`

Candidate focus pages should be audited but remain specialized:

- `PracticePage`
- `ExamTakingPage`

For focus pages:

- Keep question content layout, question navigator, timer, autosave, and answer controls specialized.
- Use shared header/state/section primitives only where they do not weaken focus mode.
- Preserve fixed right-side question navigation behavior on desktop.
- Preserve mobile bottom sheet navigation.

### 7. Admin Pages

Admin pages should migrate to the same shared primitives:

- `AdminDashboardPage`
- `AdminLoginPage`
- `ExamListPage`
- `ExamEditPage`
- `ExamCandidatesPage`
- `QuestionListPage`
- `QuestionImportPage`
- `CandidateImportPage`
- report pages using `ReportPage`

`ReportPage` can either remain as a domain-specific wrapper around `PageShell`, `PageHeader`, and `PageSection`, or be replaced only if doing so reduces duplication without hurting table/report ergonomics.

Admin requirements:

- Preserve side rail navigation.
- Preserve compact operational density.
- Preserve report filters, table actions, and import feedback flows.
- Keep mobile navigation behavior consistent with the current side rail sheet pattern.

### 8. Login Pages

Candidate login and admin login should both be clean auth canvases.

Shared rules:

- No product navigation.
- No footer.
- Use consistent Wordmark placement, page eyebrow, H1 scale, form surface, and secondary editorial panel.
- Candidate and admin login may differ in supporting copy and right-side editorial copy.

The login pages should feel like two doors into the same product, not two unrelated applications.

### 9. Microcopy Rules

Continue using `frontend/src/lib/pageCopy.ts` as the source of truth for page-level eyebrow copy.

Rules:

- No fictional `CHAPTER NN` labels at page level.
- Candidate pages use `candidatePageCopy`.
- Admin pages use `adminPageCopy`.
- Real question position may continue using `QUESTION NN · 类型 · 分值`.
- Section-level metric labels such as `QUESTIONS · 题库` can remain local if they describe real content and are not page-level eyebrows.

### 10. Accessibility And Responsive Rules

The shared primitives must preserve:

- visible `:focus-visible` rings
- semantic headings
- dialog title/description contracts
- mobile sheet navigation
- no text overlap at mobile widths
- no layout shift from dynamic button text or loading labels

Responsive expectations:

- Page headers stack cleanly below tablet width.
- Actions wrap below title/description on narrow screens.
- Admin tables keep `SimpleDataTable` mobile card behavior.
- Candidate focus navigation keeps the existing mobile sheet pattern.

## Migration Plan At Design Level

Implementation should happen in small, verified stages:

1. Add shared page primitives with tests.
2. Migrate low-risk candidate ordinary pages.
3. Migrate low-risk admin report/list pages.
4. Migrate admin dashboard and edit/import pages.
5. Audit practice and exam-taking focus pages for consistency without flattening their specialized structure.
6. Update `frontend/DESIGN.md` and targeted tests.
7. Run full frontend verification and browser QA.

Each stage should preserve behavior and visual intent before moving to the next.

## Testing Strategy

Unit/component tests should cover:

- `PageHeader` renders eyebrow, title, description, and actions.
- `PageSection` applies the expected variant classes.
- `PageState` delegates loading, empty, and error states correctly.
- Candidate ordinary pages render shared page-level structure.
- Admin pages render shared page-level structure.
- Login pages remain nav-free and footer-free.
- Existing admin import route active-state tests remain valid.
- Existing candidate focus mode tests remain valid.

Static verification:

```bash
cd frontend
npm run format:check
npm run lint
npm test
npx tsc --noEmit
npm run build
```

Browser QA should include:

- Candidate login
- Candidate exam list
- Candidate exam start
- Candidate practice
- Candidate exam taking
- Candidate result
- Admin login
- Admin dashboard
- Admin questions import
- Admin exams
- Admin reports

For each page:

- page-level eyebrow is correct
- H1 scale and spacing match the design system
- loading/empty/error states use shared components
- console has no errors or warnings
- desktop and mobile layouts do not overlap or jitter

## Acceptance Criteria

The work is complete when:

1. Candidate ordinary pages and admin ordinary pages share the same page skeleton primitives.
2. Candidate and admin navigation models remain intentionally different.
3. Candidate focus pages are audited and use shared primitives only where appropriate.
4. Login pages are clean auth canvases with no nav or footer.
5. Page-level eyebrow copy remains centralized and free of fictional chapter numbers.
6. `frontend/DESIGN.md` documents the shared page primitives and migration rules.
7. The full frontend verification suite passes.
8. Browser QA confirms no obvious desktop/mobile visual regressions.

## Risks

- Over-generalizing components could make admin workflows too spacious or candidate flows too dense.
- Migrating focus mode too aggressively could harm exam-taking clarity.
- Component abstraction could hide page-specific accessibility requirements if the API is too vague.
- Large one-shot migration could make visual regressions harder to isolate.

Mitigations:

- Keep primitives small and composable.
- Use density variants rather than separate visual systems.
- Migrate in stages with targeted tests.
- Use browser QA after each meaningful visual stage.

## Open Decisions For Implementation Planning

These decisions should be finalized in the implementation plan:

1. Whether `ReportPage` remains as an admin-specific wrapper or becomes a thin composition of shared primitives.
2. Whether `PageShell` lives under `components/page/` or `components/editorial/`.
3. Whether candidate focus pages adopt `PageShell density="focus"` immediately or only after ordinary pages are migrated.

The recommended defaults are:

- Keep `ReportPage` as a wrapper initially.
- Put new structural primitives under `components/page/`.
- Migrate focus pages last and conservatively.
