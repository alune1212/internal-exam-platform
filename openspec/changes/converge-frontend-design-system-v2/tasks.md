## 1. Establish the Live Baseline and Compatibility Guards

- [ ] 1.1 Re-read the active Windows/macOS OpenSpec deltas and record the `frontend-page-experience` requirements this change must preserve without claiming their remaining formal-host evidence.
- [ ] 1.2 Inventory every current frontend route, assign it to Auth Canvas, Candidate Calm, Admin Workbench, or Exam Focus, and record the loading/empty/error/ready/pending/confirmed-success/saved/submitted/long-content states applicable to each route.
- [ ] 1.3 Record the current production-source inventory for arbitrary typography/tracking, page-level max widths, repeated surface treatments, decorative English labels, raw colors, and documented exceptions.
- [ ] 1.4 Run and record the focused existing route, session, result-release, answer-save, submit, navigation-destination, and report-filter tests that form the behavior compatibility baseline.
- [ ] 1.5 Run the existing deterministic visual-system suite and retain its generated output only as an uncommitted before-state artifact with the exact browser and viewport environment recorded.

## 2. Rewrite the Canonical Contract and Drift Policy

- [ ] 2.1 Rewrite `frontend/DESIGN.md` as the V2 presentation contract while preserving the warm-paper palette, Academic Editorial tone, existing system-font stacks, four page families, and the explicit route/API/business compatibility boundary.
- [ ] 2.2 Add the single-owner graph for application/session boundaries, family chrome, page frames, page composition, surfaces, fields, statuses, actions, report controls, and responsive data presentation to `frontend/DESIGN.md`.
- [ ] 2.3 Define the Chinese-first product glossary and narrow English allowlist for product names and stable operational terms; document `用户` versus `应考人员` and the critical save/submit/stay/leave distinctions.
- [ ] 2.4 Add or refine semantic type, tracking, page-frame, action, control-state, 44 CSS-pixel Exam Focus touch-target, status-on-surface, overlay-viewport, and elevation roles in `src/index.css`, Tailwind aliases, and TypeScript token references without creating another token owner.
- [ ] 2.5 Correct the shared success treatment and status-border tokens so supported light and dark surfaces meet the documented contrast contract and compile to deterministic CSS.
- [ ] 2.6 Add a production-source presentation-policy check for raw colors, external or bundled fonts, unallowlisted typography/tracking, independent page widths/breakpoints, duplicated complete surfaces, unsupported motion, automatic workbench stagger, and decorative bilingual-label regressions.
- [ ] 2.7 Create a narrow, documented allowlist for state selectors, ARIA/data variants, safe-area and grid calculations, the owned identity palette, media surfaces, and other verified exceptions.
- [ ] 2.8 Add focused token, contrast, glossary, English-allowlist, and presentation-policy tests and demonstrate that representative prohibited examples fail the guard.

## 3. Establish Single Page-Frame and Family-Layout Ownership

- [ ] 3.1 Refactor the ordinary page frame to own semantic `reading`, `standard`, `wide`, and `full/focus` widths, horizontal page padding, family density, and vertical rhythm without page-level `max-w-*` overrides.
- [ ] 3.2 Remove competing candidate-layout content max-width and padding ownership while preserving browser support, candidate session, safe-return, logout, and outlet-context behavior.
- [ ] 3.3 Remove competing admin-layout content max-width ownership while preserving admin session enforcement, logout, side-rail placement, and current route rendering.
- [ ] 3.4 Introduce an explicit candidate presentation-mode boundary so auth, ordinary candidate, formal Exam Focus, and active-practice focus states can change chrome without changing route paths or session behavior.
- [ ] 3.5 Ensure the formal taking route selects Exam Focus statically and active practice requests/restores Exam Focus without hiding duplicate ordinary chrome behind an overlay.
- [ ] 3.6 Normalize only the presentation and Chinese-first copy of the unsupported-browser surface; preserve the active Windows/macOS Chrome/Safari minimum-version matrix and embedded, obsolete, and unrecognized-browser blocking behavior exactly.
- [ ] 3.7 Add layout and router tests for page-frame widths, family chrome, auth/session redirects, safe return, logout, formal focus, active-practice focus, and the unchanged route inventory.

## 4. Converge Typography, Surfaces, Statuses, and Actions

- [ ] 4.1 Refactor the shared page header so ordinary pages render one Chinese-primary H1, ordered section headings, and at most one meaningful context label without a forced eyebrow or faux chapter marker.
- [ ] 4.2 Replace repeated arbitrary type sizes and tracking in shared page, editorial, layout, admin, and exam primitives with the canonical semantic roles or documented exceptions.
- [ ] 4.3 Refine the existing section/card primitives into governed plain, panel, focus/summary, data, and overlay ownership without adding a parallel component family.
- [ ] 4.4 Remove duplicate parent-and-child background, border, radius, shadow, and padding ownership from the known shared metric, state, import, result, and workbench patterns.
- [ ] 4.5 Define and apply distinct responsibilities for page states, actionable alerts, inline status pills, and activity/status dots, including color-independent semantics.
- [ ] 4.6 Define reusable action-group contracts for auth forms, page headers, card actions, form footers, report toolbars, and destructive/guarded actions with predictable mobile reflow.
- [ ] 4.7 Add focused tests for H1/H2/H3 order, optional context labels, surface ownership, inherited async states, status semantics, action placement, and narrow-viewport reflow.

## 5. Converge Form Controls and High-Risk Interaction States

- [ ] 5.1 Consolidate input, select, and textarea shared control bases while retaining documented multiline differences and existing form values, validation, and schemas.
- [ ] 5.2 Migrate raw label/input/textarea groups in question create/edit and learning-video forms to the shared field contract for label, description, error, disabled, pending, and success association.
- [ ] 5.3 Apply the shared button pending/busy contract to real mutations, preserve independent business-disabled guards, and add a visible pressed state without layout movement.
- [ ] 5.4 Replace the learning-video visible file label trigger with a keyboard-focusable product control that activates the native file input and preserves current upload behavior.
- [ ] 5.5 Keep question/candidate import file selection on the same keyboard, focus, filename, disabled-upload, success, error, and failure-report contract.
- [ ] 5.6 Add dynamic-viewport max height, internal scrolling, safe-area spacing, accessible names, and focus reachability to shared dialogs and mobile sheets.
- [ ] 5.7 Implement native-equivalent radio-group keyboard behavior for single-choice exam options and retain checkbox semantics for multiple-choice options without changing stored answer values.
- [ ] 5.8 Replace or complete the active-attempt exit warning with description association, safe initial focus, Escape behavior, focus containment, and focus restoration while preserving navigation and unsaved-work rules.
- [ ] 5.9 Add focused keyboard and accessibility tests for fields, pending mutations, file triggers, dialog/sheet overflow, radio arrows, checkbox operation, guarded exit, focus restoration, and state contrast.

## 6. Redesign Navigation Presentation Within Existing Destinations

- [ ] 6.1 Redesign candidate desktop and mobile navigation presentation while preserving the current destination order, profile/identity access, logout, active state, and return-to-exam-list behavior.
- [ ] 6.2 Redesign admin desktop rail and mobile sheet presentation from the existing shared navigation model, preserving every destination exactly once, operational group order, active item/group semantics, and logout.
- [ ] 6.3 Keep desktop admin navigation viewport-stable and make short/mobile navigation internally scrollable so all destinations and logout remain reachable at mobile landscape and 200-percent zoom.
- [ ] 6.4 Refine exam-context navigation hierarchy and long-title wrapping while preserving only existing workspace, edit, roster/invitation, and filtered result/review destinations and their guards.
- [ ] 6.5 Add navigation tests for unchanged targets, desktop/mobile parity, active semantics, keyboard order, long labels, short viewport scrolling, logout, and the absence of a new route.

## 7. Migrate the Representative Auth and Candidate Calm Routes

- [ ] 7.1 Rewrite and recompose candidate login around the minimal Auth Canvas, Chinese-first identity/recovery copy, one primary action, and unchanged OTP/session/return behavior.
- [ ] 7.2 Recompose admin login with the same Auth Canvas contract and redesigned hierarchy while retaining the distinct admin credentials, endpoint, session, and error behavior.
- [ ] 7.3 Recompose the candidate exam list around Candidate Calm page-frame, state, status, and card-action contracts without changing invitation-aware availability or navigation targets.
- [ ] 7.4 Recompose the candidate result page around one primary outcome/score summary, attempt context available from existing route/query/result fields only, filters, and snapshot-based review in that order; add no endpoint or response field.
- [ ] 7.5 Preserve result attempt selection, pass/score truth, answer-release gating, filters, question order, saved/correct answers, analysis, awarded score, and return behavior through focused tests.
- [ ] 7.6 Add representative Auth/Candidate tests for Chinese-first copy, heading order, action placement, surface ownership, loading/error/ready states, long text, and responsive behavior.

## 8. Migrate and Harden the Representative Exam Focus Route

- [ ] 8.1 Recompose the active formal exam into dedicated task-only chrome with question, options, timer, persistence, progress, navigator, guarded exit, and submit hierarchy.
- [ ] 8.2 Remove unrelated ordinary candidate navigation from the active formal attempt while retaining a safe guarded route back to the existing exam list.
- [ ] 8.3 Apply canonical Chinese persistence and terminal-state language for pending, saving, saved, offline, conflict, error, submitted, and auto-submitted states.
- [ ] 8.4 Make desktop navigator, mobile bottom controls, mobile sheet, long options, and submit actions dynamic-viewport and safe-area aware without `100vh`-only assumptions, and enforce at least 44-by-44 CSS-pixel hit areas for Exam Focus option, navigation, guarded-exit, save, and submit actions on touch layouts.
- [ ] 8.5 Add focused Exam Focus tests for radio/checkbox semantics, question changes, persistence states, exit focus, mobile navigation, safe areas, submit distinction, auto-submit, and unchanged save/submit request behavior.

## 9. Migrate the Representative Admin Workbench Routes

- [ ] 9.1 Recompose the admin dashboard around compact Workbench hierarchy, restrained metrics, one activity/status language, and adaptive grids that do not force four narrow columns beside the rail.
- [ ] 9.2 Recompose the question list and open create/edit form state around the shared page frame, data surface, field, status, and form-footer action contracts.
- [ ] 9.3 Preserve question filters, validation, question-type behavior, create/update mutations, invalidation, and current route/API behavior through focused tests.
- [ ] 9.4 Consolidate the shared report toolbar for filters, segmented states, notices, and export actions with one desktop order and predictable mobile reflow.
- [ ] 9.5 Converge the representative score report table and responsive card representation around canonical labels, density, status, actions, and long-content handling without changing report filters or export behavior.
- [ ] 9.6 Add representative Admin tests for navigation context, dashboard hierarchy, open-form keyboard flow, pending/error/success states, report actions, responsive data presentation, and long values.

## 10. Pass the Representative Rendered Gate

- [ ] 10.1 Extend deterministic visual fixtures for the open question form, long Chinese and unbroken content, result answers released/unreleased, mobile navigation overflow, active-attempt exit, long exam options, and learning-video file/dialog states.
- [ ] 10.2 Render the seven representative route/state groups at 320x844, 375x812, 414x896, 430x932, 768x1024, and 1280x900.
- [ ] 10.3 Add representative 844x390 and 896x414 landscape, 200-percent zoom, reduced-motion, and visible-keyboard-focus checks.
- [ ] 10.4 Assert family chrome, H1 order, one-line compact labels with parent reflow, long-content bounds, uncovered required actions, safe areas, overlay scrolling, at least 44-by-44 CSS-pixel Exam Focus touch targets, control semantics, and no horizontal overflow with root clipping disabled.
- [ ] 10.5 Assert no unexpected console/API failure and retain screenshots/traces only as ignored test artifacts.
- [ ] 10.6 Fix every representative-gate regression or record a narrow approved exception before starting broad route migration.

## 11. Migrate the Remaining Candidate and Auth Routes

- [ ] 11.1 Migrate registration completion and profile editing to the Auth/Candidate field, copy, page-frame, status, and action contracts without changing account behavior.
- [ ] 11.2 Migrate learning list and video detail to Candidate Calm hierarchy, restrained surfaces, long-title handling, and existing video progress behavior.
- [ ] 11.3 Migrate practice entry and wrong-question review to Candidate Calm, then apply the dedicated Exam Focus shell only while the active practice question workspace is mounted.
- [ ] 11.4 Migrate exam start to Candidate Calm with canonical rule/status copy and unchanged eligibility, attempt-start, and navigation behavior.
- [ ] 11.5 Remove remaining unallowlisted decorative English, arbitrary typography, page widths, duplicated surfaces, and local action/status variants from candidate/auth consumers.
- [ ] 11.6 Update focused candidate/auth tests for each migrated route and preserve all invitation, registration, session, practice, learning, start, and review semantics.

## 12. Migrate the Remaining Admin Routes

- [ ] 12.1 Migrate account directory and question import to Workbench page-frame, field, data, import, status, and action contracts.
- [ ] 12.2 Migrate admin exam list, aggregate workspace, editor, and candidate roster to Workbench hierarchy, exam context, fields, statuses, responsive data, and guarded actions.
- [ ] 12.3 Preserve workspace privacy/freshness/next-action semantics, publish readiness, question rules, roster/invitation actions, retake behavior, and current routes/APIs through focused tests.
- [ ] 12.4 Migrate learning content management, file-selection, and edit dialog states to the shared field, overlay, status, and action contracts.
- [ ] 12.5 Migrate learning, question-accuracy, wrong-question, and absent-candidate reports to the shared report toolbar, data, copy, state, and export contracts.
- [ ] 12.6 Replace the operations status-card wall with a restrained Workbench status/data pattern while preserving the same readiness signals and actions.
- [ ] 12.7 Remove remaining unallowlisted decorative English, arbitrary typography, page widths, duplicated surfaces, local status systems, and action-layout variants from admin consumers.
- [ ] 12.8 Update focused admin tests for each migrated route and preserve all query, mutation, import, report, export, readiness, and authorization behavior.

## 13. Complete Route-Wide Responsive and Accessibility Acceptance

- [ ] 13.1 Map every current route to deterministic applicable states in the visual route inventory and fail the suite when a router destination is missing from that inventory.
- [ ] 13.2 Render all applicable route/state groups across the required mobile, tablet, desktop, landscape, zoom, and reduced-motion matrix, sharding execution without weakening coverage.
- [ ] 13.3 Verify root overflow with clipping disabled, visible element bounds, long text, compact-label reflow, fixed/sticky coverage, dynamic-viewport overlays, safe-area controls, and at least 44-by-44 CSS-pixel Exam Focus touch targets.
- [ ] 13.4 Verify keyboard reachability and visible focus for navigation, fields, filters, files, dialogs, sheets, options, guarded exit, save, submit, and report actions.
- [ ] 13.5 Verify loading, empty, error, stale, pending, confirmed-success, saved, offline, conflict, submitted, and auto-submitted states only on routes where those states are behaviorally applicable.
- [ ] 13.6 Resolve every route-wide browser, console, hierarchy, copy, containment, focus, contrast, overflow, or source-policy regression; document only narrow intentional exceptions.

## 14. Run Final Verification and Record Evidence

- [ ] 14.1 Run `npm run format:check` from `frontend/` and resolve only formatting introduced by this change.
- [ ] 14.2 Run `npm test -- --run` from `frontend/` and resolve all affected unit/component regressions.
- [ ] 14.3 Run `npm run lint`, `npm run build`, and `npm run check:offline` from `frontend/`; confirm no new package, external font, or external asset dependency entered scope.
- [ ] 14.4 Run `npm run test:e2e:visual` from `frontend/` and `sh ops/e2e/run-browser-gate.sh` from the repository root; record exact passed, failed, skipped, browser, route, state, and viewport evidence without claiming formal host acceptance.
- [ ] 14.5 Run the presentation-policy scans and disposition every remaining exception by owner and reason.
- [ ] 14.6 Update `frontend/DESIGN.md` to match the implemented contract and update `docs/handoff.md` only with commands and browser evidence actually observed.
- [ ] 14.7 Run `openspec validate --all --strict --no-interactive` and `git diff --check`, then inspect the final diff for backend, route, API, auth, snapshot, scoring, save, submit, import, report, dependency, or unrelated-refactor scope drift.
