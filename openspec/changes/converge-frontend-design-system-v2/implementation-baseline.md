# Frontend Design Convergence V2 Implementation Baseline

Captured on 2026-08-14 from commit `908748c`. This document is the reproducible
before-state for implementation. It records product behavior and portability
constraints that the presentation redesign must preserve; it is not formal
Windows or macOS host-acceptance evidence.

## 1. Active Portability and Reliability Requirements

The active changes `stabilize-windows-internal-exam-platform` and
`support-macos-formal-host-portability` remain authoritative for their unfinished
host evidence. V2 must preserve the following frontend requirements.

| Area | Requirement preserved by V2 |
| --- | --- |
| Browser support | Support the documented Windows Edge/Chrome, Android Chrome, iOS Safari, and current macOS Chrome/Safari minimums. Continue to block obsolete, embedded, legacy, and unrecognized browsers with an explicit explanation. Presentation or Chinese copy may change; detection rules may not. |
| Answer synchronization | Distinguish pending, saving, saved, offline, conflict, and failed states. Never claim an answer is saved before server confirmation. Preserve retry and takeover actions. |
| Draft recovery | Keep session-scoped draft storage keyed by candidate, attempt, generation, and revision; restore eligible unsaved work and clear it after submission or invalidation. |
| Offline runtime | Keep fonts, scripts, styles, and product runtime assets same-origin and free of third-party CDN, analytics, or remote-font requests. |
| Accessibility | Preserve semantic labels, keyboard and focus behavior, announced states, contrast, zoom support, and non-overlapping mobile controls as release gates. |
| Browser E2E | Preserve the Nginx/backend/PostgreSQL flow for publish, candidate access, start, save, reload, submit, result release, conflict handling, and session invalidation. |
| Operations states | Keep each signal distinguishable as loading, current, degraded, stale, skipped, or failed. A partial failure must not render as healthy, empty, or zero. |
| Exam decomposition | Preserve routes, tokens, snapshots, question navigation, server-based countdown, save-before-submit, and existing desktop/mobile behavior while presentation changes. |
| Formal-host evidence | Static inspection, builds, disposable containers, Vite fixtures, and local Chrome screenshots do not satisfy formal Windows or macOS commissioning. Record the host, browser, route, state, and viewport for any rendered evidence. |
| Data and writer boundary | Formal deployment still requires verified paired database/media backups, checksums, migration/count/sample validation, an independent encrypted copy, and exactly one active writer with explicit cutover evidence. |
| Rollback | Keep the active same-host and cross-host rollback/data-loss confirmation rules; this frontend change does not weaken them. |

Source requirements:

- `openspec/changes/stabilize-windows-internal-exam-platform/specs/frontend-page-experience/spec.md`
- `openspec/changes/support-macos-formal-host-portability/specs/frontend-page-experience/spec.md`
- `openspec/changes/support-macos-formal-host-portability/specs/formal-host-portability/spec.md`
- `openspec/changes/converge-frontend-design-system-v2/specs/frontend-page-experience/spec.md`

## 2. Route, Family, and State Inventory

`frontend/src/app/router.tsx` is the route authority. The snapshot contains 29
entries: 27 leaf paths plus the `/` and `/admin` redirects. `RouteErrorPage` is a
cross-cutting error boundary for both candidate and admin trees.

State vocabulary in this table is deliberately exhaustive for each route. A
state listed as stale means server-backed content may remain visible while a
refresh or refetch is pending; it does not authorize falsely labeling failed
data as current.

| Route | Family | Applicable states |
| --- | --- | --- |
| `/` | Auth Canvas | redirect |
| `/login` | Auth Canvas | ready, pending, error |
| `/register` | Auth Canvas | ready, pending, error, long-content |
| `/profile` | Candidate Calm | loading, error, ready, pending, confirmed-success, long-content, stale |
| `/learning` | Candidate Calm | loading, error, empty, ready, long-content, stale |
| `/learning/:videoId` | Candidate Calm | loading, error, ready, pending, confirmed-success, long-content, stale |
| `/practice` | Candidate Calm before a question workspace; Exam Focus while active | loading, error, empty, ready, pending, saved/confirmed-success, submitted, long-content, stale |
| `/practice/wrong-questions` | Candidate Calm | loading, error, empty, ready, long-content, stale |
| `/exams` | Candidate Calm | loading, error, empty, ready, long-content, stale |
| `/exams/:examId/start` | Candidate Calm | loading, error, ready, pending, long-content, stale |
| `/exams/:examId/taking` | Exam Focus | not-started, loading, error/session-conflict, empty, ready, pending, saving, saved, offline, conflict, failed, submitted, auto-submitted, long-content |
| `/exams/:examId/result` | Candidate Calm | loading, error, empty, ready, submitted outcome, released/unreleased answers, long-content, stale |
| `/admin/login` | Auth Canvas | ready, pending, error |
| `/admin` | Admin Workbench | redirect |
| `/admin/dashboard` | Admin Workbench | loading, error, empty activity, ready, long-content, stale |
| `/admin/accounts` | Admin Workbench | loading, error, empty, ready, pending, confirmed-success, long-content, stale |
| `/admin/questions` | Admin Workbench | loading, error, empty, ready, pending, confirmed-success, long-content, stale |
| `/admin/questions/import` | Admin Workbench | ready/empty-selection, pending, error, confirmed-success, long-content |
| `/admin/exams` | Admin Workbench | loading, error, empty, ready, pending, long-content, stale; create success navigates to the existing destination |
| `/admin/exams/:examId` | Admin Workbench | loading, error/missing, ready, long-content, stale |
| `/admin/exams/:examId/edit` | Admin Workbench | loading, error/missing, ready, pending, confirmed-success, long-content |
| `/admin/exams/:examId/candidates` | Admin Workbench | loading, error/missing, empty, ready, pending, confirmed-success, long-content |
| `/admin/learning` | Admin Workbench | loading, error, empty, ready, pending, confirmed-success, long-content |
| `/admin/learning/reports` | Admin Workbench | loading, error, empty, ready, pending, confirmed-success, long-content, stale |
| `/admin/reports/scores` | Admin Workbench | loading, error, empty, ready, pending, confirmed-success, long-content, stale |
| `/admin/reports/questions` | Admin Workbench | loading, error, empty, ready, pending, confirmed-success, long-content, stale |
| `/admin/reports/wrong` | Admin Workbench | loading, error, empty, ready, pending, confirmed-success, long-content, stale |
| `/admin/reports/absent` | Admin Workbench | loading, error, empty, ready, pending, confirmed-success, long-content, stale |
| `/admin/operations` | Admin Workbench | loading, error, ready, stale; per-signal current, degraded, stale, skipped, failed; long-content |

Known presentation mismatch retained as evidence: ordinary candidate chrome is
still rendered by `CandidateLayout` for the formal taking route. V2 must select
dedicated Exam Focus chrome without changing the route, session, return, save,
or submission contracts.

## 3. Production-Source Drift Inventory

Scope: 125 production files under `frontend/src`, excluding test/spec files and
test directories.

| Signal | Before count |
| --- | ---: |
| Arbitrary `text/font/leading/tracking-[...]` utilities | 68 |
| Arbitrary tracking utilities (subset) | 55 |
| Other arbitrary text/font/leading utilities (subset) | 13 |
| `max-w-*` utilities | 43 |
| `PageShell` tags carrying a local `max-w-*` | 19 |
| Layout-level `max-w-*` in candidate/admin/top navigation | 4 |
| Static complete surfaces combining radius, border, background, and padding | 24 |
| Complete surfaces that also own shadow/elevation | 12 |
| `PageSection` card/panel/table consumers | 25 |
| `PageSection` consumers adding local padding/radius overrides | 9 |
| English-plus-Han middle-dot literal lines | 125 across 14 files |
| Lines in `pageCopy.ts` containing those middle-dot labels | 92 |
| `uppercase` utility occurrences | 47 |
| Raw hex literals | 24 |
| Raw `rgb/rgba/hsl/hsla` literals | 6 |

Reproduction commands:

```bash
rg --files frontend/src \
  | rg -v '(^|/)(__tests__|test|tests)(/|$)|\.(test|spec)\.(ts|tsx|js|jsx)$' \
  | wc -l

rg -o --pcre2 '(?:text|font|leading|tracking)-\[[^]]+\]' frontend/src \
  --glob '!**/*.test.*' --glob '!**/*.spec.*' \
  --glob '!**/__tests__/**' --glob '!**/test/**' | wc -l

rg -o --pcre2 '\bmax-w-(?:[A-Za-z0-9_-]+|\[[^]]+\])' frontend/src \
  --glob '!**/*.test.*' --glob '!**/*.spec.*' \
  --glob '!**/__tests__/**' --glob '!**/test/**' | wc -l

rg -n --pcre2 -o 'className="[^"]*"' frontend/src \
  --glob '!**/*.test.*' --glob '!**/*.spec.*' \
  --glob '!**/__tests__/**' --glob '!**/test/**' \
  | rg --pcre2 '(?=.*\brounded(?:-[^ ]+)?)(?=.*\bborder(?:-[^ ]+)?)(?=.*\bbg-[^ ]+)(?=.*\b(?:p|px|py|pt|pb|pl|pr)-[^ ]+)' \
  | wc -l

rg -n --pcre2 '"[^"\n]*[A-Za-z][^"\n]*·[^"\n]*[\p{Han}]|`[^`\n]*[A-Za-z][^`\n]*·[^`\n]*[\p{Han}]' frontend/src \
  --glob '!**/*.test.*' --glob '!**/*.spec.*' \
  --glob '!**/__tests__/**' --glob '!**/test/**' | wc -l
```

Representative drift includes arbitrary typography in `ui/label.tsx`,
`ui/button-variants.ts`, `ui/card.tsx`, and `ExamResultPage.tsx`; competing width
ownership in `PageShell`, `CandidateLayout`, `AdminLayout`, and `TopNav`; repeated
exam state and list-card surfaces; decorative labels concentrated in
`lib/pageCopy.ts`; and consumer color shortcuts such as video black, admin-rail
white alpha, and status alpha borders.

Documented exceptions are not drift:

- `src/index.css :root` owns runtime color, font, type, spacing, and motion literals.
- `src/lib/breakpoints.ts` owns structural breakpoints.
- `src/lib/pastelPalette.ts` owns the data-derived identity palette.
- Auth Canvas and Exam Focus may use their documented specialized frames.
- State/ARIA/data selectors, safe-area calculations, responsive grid calculations,
  owned media surfaces, and deep family chrome remain narrow allowlisted cases.
- `NamePlate` may consume the owned identity palette through `pickPastel()`.

## 4. Behavior Compatibility Baseline

Executed from `frontend/` with Vitest 4.1.9 and Node 26.7.0:

```bash
npm test -- --run \
  src/pages/P0Pages.test.tsx \
  src/pages/ExamStartPage.test.tsx \
  src/components/layout/__tests__/CandidateLayout.test.tsx \
  src/components/layout/__tests__/AdminLayout.test.tsx \
  src/lib/candidateSession.test.ts \
  src/lib/adminSession.test.ts \
  src/pages/admin/AdminLoginPage.test.tsx \
  src/components/layout/__tests__/TopNav.test.tsx \
  src/components/layout/__tests__/AdminSideRail.test.tsx \
  src/components/admin/__tests__/ExamContextNav.test.tsx \
  src/features/exam/useAttemptDraftQueue.test.tsx \
  src/features/exam/ExamTakingWorkspace.test.tsx \
  src/pages/admin/ScoreReportPage.test.tsx \
  src/pages/admin/LearningReportPage.test.tsx \
  src/api/reports.test.ts
```

Result: 15 files and 117 tests passed, 0 failed. Vitest duration was 6.20
seconds; wall time was 6.95 seconds.

Baseline gaps to close during implementation:

- no Vitest file imports the production `src/app/router.tsx`; existing route
  tests use partial memory routers;
- candidate unauthorized redirect and safe return are covered, while the
  no-token `AdminLayout` redirect lacks a focused assertion;
- score, accuracy, wrong-question, and learning filters are covered; the absent
  candidate filter lacks a focused assertion.

## 5. Deterministic Rendered Before State

Executed from `frontend/`:

```bash
npm run test:e2e:visual
```

Environment and result:

- Vite 8.0.16 fixture servers on `127.0.0.1:18080` and `127.0.0.1:18081`;
  both were stopped after the run.
- Playwright 1.54.2 project `chromium-visual-system` using Google Chrome stable
  channel 151.0.7922.109 because bundled Chromium was unavailable.
- 154 passed, 0 failed, 0 skipped in 275.84 seconds.
- Viewports: 320x844, 375x812, 414x896, 430x932, 768x1024, 1280x900,
  896x414, and 844x390, plus reduced-motion and 200-percent zoom cases.
- 159 ignored PNGs, approximately 11 MB, retained at
  `.runtime/e2e/browser-output/visual-system-baseline-task-1-5-chrome/`.
- The Vite-only fixture emitted delayed proxy warnings for intentionally pending
  save requests; all Playwright assertions remained green.

These screenshots are an uncommitted local before-state artifact. They prove the
fixture suite passed in the environment above, not that a formal host, network,
browser matrix, native build, restart recovery, or data migration was accepted.
