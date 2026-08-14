## 1. Establish the Baseline and Preserve Boundaries

- [x] 1.1 Run `npm run format:check`, `npm test -- --run`, `npm run lint`, `npm run build`, and `npm run check:offline` from `frontend/`; record the pre-change result and isolate any unrelated existing failure before visual edits.
- [x] 1.2 Extend layout regression tests to lock Candidate Calm, Admin Workbench, Auth Canvas, and Exam Focus shell boundaries, including the intentional absence of a global footer and product navigation on auth routes.
- [x] 1.3 Add focused regression assertions around the admin workspace last-good-data behavior and the exam focus save, offline, conflict, submit, and auto-submit presentations so composition changes cannot silently change their existing behavior.
- [x] 1.4 Create a representative route/state inventory for candidate, admin, auth, and focus browser checks, using existing API mocks or fixtures and no new backend endpoint.

## 2. Establish the Canonical Token and Font Source

- [x] 2.1 Expand `frontend/src/index.css :root` with named semantic type-size/line-height, page/section/control spacing, focus, motion, and z-layer tokens while retaining the existing color, radius, shadow, and offline-safe font values.
- [x] 2.2 Make the existing Iowan/Palatino/Songti display stack, system UI/PingFang/Microsoft YaHei body stack, and platform monospace stack the documented runtime font contract; remove Source Serif 4, Inter, and JetBrains Mono claims from governed mirrors.
- [x] 2.3 Add `frontend/src/lib/breakpoints.ts` as the sole typed structural-width map; import it from `tailwind.config.ts` and `src/lib/use-media-query.ts`, and remove their independent `768px`/`1024px` breakpoint literals.
- [x] 2.4 Update `frontend/tailwind.config.ts` so explicit colors, fonts, type-size/line-height values, semantic spacing, radii, shadows, motion, and z-layers consume CSS variables while responsive screens consume the typed breakpoint map.
- [x] 2.5 Keep the `designTokens` export in `frontend/src/lib/design-tokens.ts`, but replace every governed raw value with its exact `var(--token-name)` reference; do not add an alternative raw-value accessor.
- [x] 2.6 Expand token tests to compare governed CSS token names, Tailwind aliases, `designTokens` references, breakpoint and media-query consumers, font ownership, z-layers, contrast contracts, and the prohibition on external font requests.
- [x] 2.7 Move the admin-login decorative gradient or texture into a named CSS treatment and document `pastelPalette.ts` as the single data-derived avatar-color exception rather than a general UI palette.
- [x] 2.8 Run the focused token, breakpoint, contrast, and offline-asset tests and fix all parity failures before migrating shared components.

## 3. Normalize Typography and Page Hierarchy

- [x] 3.1 Change `PageHeader` so its context/eyebrow content is optional, stacked above the title when present, and omitted from the DOM when it adds no meaning; cover both variants with component tests.
- [x] 3.2 Change `ChapterNumber` from a mandatory italic page-label pattern into an upright semantic ordinal/context treatment, keeping it only where a real sequence or position is communicated.
- [x] 3.3 Define shared upright H1/H2/H3 and context-label contracts using canonical tokens, with safe CJK and long-word wrapping and no fixed-height title containers.
- [x] 3.4 Migrate `ExamListPage`, `ExamStartPage`, `LearningListPage`, and `ProfilePage` to one H1 and at most one allowlisted context label that conveys real route, state, or workflow meaning; remove only decorative pairs and update affected `pageCopy`/page tests without changing H1 terminology.
- [x] 3.5 Migrate `ExamResultPage`, `WrongQuestionReviewPage`, `PracticePage`, and the exam focus components to ordered heading levels and upright semantic labels while preserving genuine question-position and status context.
- [x] 3.6 Migrate admin dashboard, list/import, workspace, and report headers to the same one-H1/ordered-H2-H3 hierarchy without reducing workbench density or changing business terminology.
- [x] 3.7 Remove italic styling from status, action, question, metric, navigation, wordmark, and name-plate labels in `ExamNavigator`, `MetricCard`, `NamePlate`, `Wordmark`, and related call sites; allow remaining italics only through one documented prose/quotation-only class or variant.
- [x] 3.8 Add hierarchy tests for one H1 and ordered H2/H3 descendants, with an explicit Exam Focus exception for its specialized heading structure, plus an allowlist-based policy check for meaningful context labels and the prose-only italic exception.

## 4. Enforce Surface Containment

- [x] 4.1 Keep the existing `PageSection` API `plain | panel | card | table`, define `card` as the focus-card semantics when the section owns emphasis, and encode one-owner border/radius/background/shadow rules across `PageSection`, standalone `Card`, and metric primitives without adding another variant.
- [x] 4.2 Flatten the known nested metric-card group in `ExamWorkspacePage` while preserving its observation time, next action, readiness, aggregate values, stale behavior, and deep links.
- [x] 4.3 Audit `AdminDashboardPage` and the remaining non-metric sections of `ExamWorkspacePage`; convert duplicated containment to one owned surface per summary group without changing data or actions.
- [x] 4.4 Audit `ExamEditPage`, `ExamCandidatesPage`, `QuestionImportPage`, and `CandidateImportPage`; flatten duplicated form/import containment while preserving validation and primary actions.
- [x] 4.5 Audit `ScoreReportPage`, `QuestionAccuracyPage`, `WrongQuestionPage`, `AbsentCandidatePage`, `LearningReportPage`, and `OperationsPage`; keep each filter/table/state region to one containment owner.
- [x] 4.6 Audit `ExamListPage`, `ExamStartPage`, `ExamResultPage`, `LearningListPage`, `WrongQuestionReviewPage`, `PracticePage`, and `ProfilePage`; use plain sections/rules for ordinary grouping and focus cards only for emphasized objects.
- [x] 4.7 Add an inherited-surface mode to `PageState`/its loading skeleton and migrate embedded page states so loading, empty, error, and stale feedback do not create a card inside `PageSection card|panel|table`.
- [x] 4.8 Add component/page tests for every surface variant, metric grouping, and inherited async state.

## 5. Unify Form and Stateful Control Primitives

- [x] 5.1 Extend `Field` to own label, description, error association, and documented disabled, pending, invalid, and success state attributes without changing form schemas.
- [x] 5.2 Add a shared native `Select` primitive with the same height, spacing, typography, focus-visible, disabled, invalid, and success contracts as `Input` and `Textarea`; do not introduce a custom combobox dependency.
- [x] 5.3 Align `Input`, `Textarea`, `Button`, file-picker, segmented-control, and `Select` transitions and state styling with canonical focus and motion tokens.
- [x] 5.4 Migrate raw admin selects in account, question, exam-edit, learning-report, and report-filter surfaces to the shared primitive while preserving values, query parameters, and validation.
- [x] 5.5 Migrate candidate wrong-question/review and any remaining repeated native select treatment to the shared primitive while preserving native keyboard behavior.
- [x] 5.6 Add unit and interaction tests for field association, keyboard use, selected state, visible focus, disabled/pending mutation guards, invalid feedback, and color-independent success/error communication.

## 6. Apply the Page-Family Composition Contracts

- [x] 6.1 Normalize `ExamListPage`, `ExamStartPage`, and `LearningListPage` around Candidate Calm `PageShell`, header, section, state, and action composition.
- [x] 6.2 Normalize `ExamResultPage`, `WrongQuestionReviewPage`, and `ProfilePage` around Candidate Calm density while preserving result filters, review semantics, and profile validation.
- [x] 6.3 Normalize admin content/configuration surfaces—account directory, question list/import, exam list/edit/candidates, and learning content—around Admin Workbench density and scan-friendly actions.
- [x] 6.4 Normalize admin operational/review surfaces—dashboard, exam workspace, operations, and report pages—around Admin Workbench status, filter, table, and action composition.
- [x] 6.5 Keep `LoginPage`, `RegistrationPage`, and `AdminLoginPage` in the chrome-free Auth Canvas while applying shared hierarchy, field, notice, and primary-action contracts.
- [x] 6.6 Keep `ExamTakingWorkspace` and the active `PracticePage` interface in Exam Focus composition; preserve timer, options, persistence/recovery, navigator, progress, and submit reachability without adding an ordinary page header.
- [x] 6.7 Consolidate pending, saving, saved, stale, offline, conflict, error, submitted, and auto-submitted visible labels through existing typed copy/status boundaries rather than raw API codes.
- [x] 6.8 Update page/component tests for each family batch to assert density, heading order, primary action, and state treatment without changing route or API expectations.

## 7. Reorganize Admin Navigation Without Changing Routes

- [x] 7.1 Define one typed admin navigation model grouped as 概览, 内容, 考试, 复盘, and 系统, mapping every current primary destination exactly once and preserving canonical labels.
- [x] 7.2 Render the shared grouped model in the desktop side rail and mobile sheet with matching order, active group/item semantics, viewport-stable desktop behavior, and reachable logout.
- [x] 7.3 Add `frontend/src/components/admin/ExamContextNav.tsx` with accessible links for existing workspace, configuration, roster/invitation, and result/review destinations; keep monitoring inside the workspace and do not add a route.
- [x] 7.4 Integrate exam context into the existing workspace, exam-edit, and exam-candidate surfaces without duplicating the advisory next action or bypassing any mutation/readiness guard.
- [x] 7.5 Update `AdminSideRail` tests, add `ExamContextNav` tests, and update `ExamWorkspacePage`, `ExamEditPage`, and `ExamCandidatesPage` tests for destination coverage, active state, keyboard behavior, logout, existing deep links, and the absence of a new route.

## 8. Complete Motion and Responsive Hardening

- [x] 8.1 Route motion in `src/index.css`, `tailwind.config.ts`, shared button/input/textarea/skeleton/spinner/dialog/sheet components, and `components/exam/Timer.tsx` through the named duration and easing tokens; retain only direct feedback, Sheet/Dialog transitions, and explicitly allowed page entry.
- [x] 8.2 Add complete `prefers-reduced-motion` alternatives that stop shimmer, pulse, zoom, stagger, and nonessential translation while retaining static loading, critical, selected, and focus signals; Timer critical state remains static text/color under reduction.
- [x] 8.3 Remove or disable automatic `PageShell`/`data-stagger` animation on Admin Workbench rows and card grids; restrict any remaining opt-in stagger to documented Candidate/Auth orientation cases and cover the allowlist in tests.
- [x] 8.4 Detect and fix oversized boxes before containment, add long-heading wrapping, one-line compact action labels with parent reflow, responsive section actions, and mobile safe-area spacing; add root `overflow-x: clip` only afterward as decorative/transition paint protection and never as the overflow assertion.
- [x] 8.5 Verify table-to-card behavior, candidate top navigation, admin rail/sheet transitions, and Exam Focus desktop/mobile transitions against the shared `breakpoints.ts` thresholds and remove remaining independent JS width literals.
- [x] 8.6 Add focused CSS/component tests for tokenized motion, reduced-motion coverage, immediate focus rings, safe-area controls, and the prohibition on ungoverned duration/easing values.

## 9. Add Rendered Multi-Viewport Acceptance

- [x] 9.1 Add `frontend/e2e/fixtures/visual-system.ts` with reusable route interception, authenticated candidate/admin state, and deterministic ready/loading/error/stale/saving/saved/offline/conflict/submitted state builders; do not depend on replaying the mutable formal-exam seed.
- [x] 9.2 Add a `chromium-visual-system` project to `frontend/playwright.config.ts` whose `testMatch` includes `visual-system.spec.ts`, and add a reproducible `test:e2e:visual` package script so the suite cannot silently report no tests.
- [x] 9.3 Add `frontend/e2e/visual-system.spec.ts` and write disposable artifacts below the configured Playwright output directory as `visual-system/<family>/<route>-<viewport>.png`; keep the output ignored and uncommitted.
- [x] 9.4 Cover Auth Canvas and Candidate Calm at 320x844, 375x812, 414x896, 430x932, 768x1024, and 1280x900, including validation, list/detail, and result/review states.
- [x] 9.5 Cover Admin Workbench at the same viewport matrix, including grouped mobile/desktop navigation, dashboard/list, form, exam context, workspace stale state, and report actions.
- [x] 9.6 Cover Exam Focus at the same viewport matrix, including question/options, timer, saving/saved/offline/conflict states, mobile navigator sheet, safe-area bottom controls, and submit.
- [x] 9.7 Add mobile-landscape checks at 844x390 and 896x414 plus 200-percent zoom and reduced-motion spot checks, including visible focus and keyboard navigation.
- [x] 9.8 Assert overflow with root clipping disabled and visible-element bounds inspected; assert compact labels remain one line by comparing their box height with computed line-height; also assert heading order, required-action reachability, no coverage, and no unexpected console error, with the documented specialized Exam Focus heading exception.

## 10. Rewrite the Canonical Documentation

- [x] 10.1 Rewrite the foundations of `frontend/DESIGN.md` with scope, principles, ownership graph, complete token tables, actual offline font stacks, CJK fallbacks, and the documented avatar-palette exception.
- [x] 10.2 Add the Candidate Calm, Admin Workbench, Exam Focus, and Auth Canvas route/composition matrix, including grouped admin and exam-context navigation and the explicit no-global-footer rule.
- [x] 10.3 Add typography/context-label rules, surface containment, shared component ownership, form/control states, async/state language, and bilingual content guidance.
- [x] 10.4 Add accessibility, focus, motion/reduced-motion, safe-area, breakpoint, 320/375/414/430/768/desktop, mobile-landscape, 200-percent zoom, and rendered-evidence acceptance contracts.
- [x] 10.5 Add source ownership, drift-check expectations, change governance, verification commands, and a changelog entry to `frontend/DESIGN.md`.
- [x] 10.6 Update `docs/handoff.md` only with actually observed command and browser results, the exact environment/viewports, remaining risks, and the distinction between disposable engineering evidence and formal Mac/Windows acceptance.

## 11. Run Final Verification and Scope Review

- [x] 11.1 Run `npm run format:check` from `frontend/` and resolve only formatting introduced by this change.
- [x] 11.2 Run `npm test -- --run` from `frontend/` and resolve all affected unit/component regressions.
- [x] 11.3 Run `npm run lint`, `npm run build`, and `npm run check:offline` from `frontend/`; confirm there is no new dependency or external font/asset request.
- [x] 11.4 Run `sh ops/e2e/run-browser-gate.sh` from the repository root, confirm its Playwright output includes `chromium-visual-system` plus the existing formal-exam desktop/mobile projects, and record passed, failed, and skipped evidence accurately.
- [x] 11.5 Run targeted static scans for raw selects, italic headings/status/actions/question/metric/navigation labels outside the prose-only allowlist, ad-hoc visual literals, legacy HSL tokens, external font URLs, automatic workbench staggering, independent breakpoint/z-index literals, and known nested-card patterns; disposition every remaining match as governed or out of scope.
- [x] 11.6 Run `openspec validate --all --strict --no-interactive` and `git diff --check`, then review the final diff to confirm no backend, API, route, auth, workspace semantic, or exam-delivery change entered scope.
