## Context

The frontend uses the Academic Editorial system defined in `frontend/DESIGN.md`. The shared token layer and most page primitives are already in place, but the review found inconsistent handling of query states, admin edit readiness, heading hierarchy, and local form/accessibility details across candidate and admin pages.

The change is cross-cutting within the React frontend. It touches candidate workflows, admin reports, admin editing, shared report/table components, and page-level primitives, but it does not change backend APIs, persistence, authentication, exam snapshot semantics, import limits, or deployment.

## Goals / Non-Goals

**Goals:**
- Make required query states explicit: loading, empty, and error must render differently and must not be collapsed into the same UI.
- Prevent admin pages from exposing mutation actions that depend on data which has not loaded yet.
- Keep candidate and admin pages aligned with `frontend/DESIGN.md` while preserving their different navigation models.
- Improve local accessibility for heading hierarchy, segmented controls, custom dropdowns, and feedback announcements.
- Add focused tests and browser checks for the changed frontend surfaces.

**Non-Goals:**
- No backend endpoint changes, schema changes, auth changes, or data migrations.
- No dependency additions or replacement of the design system.
- No LMS, anti-cheat, complex RBAC, queue, or document-format expansion.
- No broad visual redesign beyond hardening existing Academic Editorial patterns.

## Decisions

### Use Existing Page-State Primitives

Use `PageState` for page-level loading, empty, and error outcomes, and use existing section/table skeletons only where the surrounding page shell and header are already stable. This keeps the implementation local and avoids adding a new state framework.

Alternative considered: introduce a generic query-state wrapper for every page. That would reduce repetition, but it would add abstraction before the current page-specific edge cases are understood. The first pass should keep behavior explicit at the affected pages and shared report wrapper.

### Treat Missing Required Data as a Blocking State

Pages such as exam edit and exam-candidate management depend on fetched records before safe actions can be shown. These pages should render loading/error/not-found states before editable defaults or destructive controls appear.

Alternative considered: keep rendering forms with disabled actions while data loads. That still exposes default values and creates a confusing visual state. A clear page state is safer and easier to test.

### Preserve Specialized Exam Focus Layouts

`PracticePage` and `ExamTakingPage` may keep specialized focus-mode question layouts, timers, navigators, and mobile Sheets. The hardening should only normalize their early-return states and query error handling, not force ordinary `PageHeader` composition into the active question workflow.

Alternative considered: convert focus-mode pages fully to ordinary page primitives. That would conflict with `frontend/DESIGN.md`, which explicitly allows these workflows to remain specialized.

### Prefer Native or Existing Accessible Controls

When a control is stateful, it must expose semantic state. Segmented controls should expose `aria-pressed` or an equivalent selected-state model. Custom dropdowns should either become native controls or implement complete label association, keyboard, and focus behavior.

Alternative considered: keep visual-only controls and rely on surrounding text. That keeps visual output stable but leaves keyboard and assistive-technology users with inconsistent state.

## Risks / Trade-offs

- [Risk] Over-generalizing page-state wrappers could make exam focus workflows feel less direct. → Mitigation: limit generic treatment to page-level and early-return states; keep active exam/practice layouts specialized.
- [Risk] Treating every background refetch error as a blocking page error could hide useful stale data. → Mitigation: distinguish initial required-load failures from background refetch failures when implementing with TanStack Query.
- [Risk] Replacing custom controls could slightly change layout density. → Mitigation: preserve existing token aliases, radius rules, and local UI primitives.
- [Risk] Browser-only overlap issues may remain after static changes. → Mitigation: include mobile screenshots for focus-mode bottom controls and report action wrapping.
