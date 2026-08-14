## 1. Backend Exam Workspace

- [x] 1.1 Add Pydantic workspace summary and next-action schemas without roster identity fields.
- [x] 1.2 Implement grouped exam workspace aggregation with one observation time, draft readiness, latest-attempt attendance, raw attempt, invitation, and incident counts.
- [x] 1.3 Derive the documented advisory next-action precedence and expose the admin-only workspace route.
- [x] 1.4 Add service and HTTP contract tests for authorization, missing exams, summary reconciliation, retake/void/in-flight states, and next actions.

## 2. Exam Lifecycle Consistency

- [x] 2.1 Acquire the shared lifecycle mutex before a new-attempt eligibility decision and lock/reload the exam in the start transaction while preserving read-only resume.
- [x] 2.2 Lock every status-changing exam update and preserve the existing in-progress admin write gate.
- [x] 2.3 Make ordinary exam updates and their allowlisted admin audit event commit atomically while retaining the specialized publish audit.
- [x] 2.4 Add PostgreSQL concurrency coverage for both start-versus-archive orderings and rerun existing start/start, snapshot, retake, save, and submit tests.

## 3. Admin Exam Workspace Frontend

- [x] 3.1 Add typed workspace API access and stable exam-scoped query keys in `frontend/src/api/`.
- [x] 3.2 Add `/admin/exams/:examId`, link exam titles to it, and compose the page from existing Academic Editorial primitives.
- [x] 3.3 Render lifecycle summaries, `observed_at`, advisory reason, and deep links to existing publish/roster/invitation/incident/result/archive surfaces.
- [x] 3.4 Poll only active workspaces at the bounded interval, stop when archived, and invalidate workspace data after exam-scoped mutations.
- [x] 3.5 Add component tests for loading, missing/error, summary, next-action, polling, and responsive action behavior.

## 4. Recoverable Query And Route States

- [x] 4.1 Extend shared page-state composition for retry actions and cached-data refresh warnings with last-success time.
- [x] 4.2 Apply recoverable first-load and stale-refresh behavior to the named candidate exam, practice, learning, review, and result queries.
- [x] 4.3 Apply recoverable first-load and stale-refresh behavior to shared reports, account directory, operations, and dashboard queries.
- [x] 4.4 Add a lazy-route error boundary with user-triggered reload and safe-home actions and no automatic reload loop.
- [x] 4.5 Add focused tests for error-to-retry success, stale cached data, expired-session handling, and chunk-load failure.

## 5. Candidate Interruption And Accessibility

- [x] 5.1 Extend the serialized draft queue for immediate offline state, visible/online retry, hidden/page-exit persistence, and an explicit unsynchronized-state signal.
- [x] 5.2 Guard browser and in-app navigation only while an active attempt has unsynchronized work, preserving same-tab session storage and single-submit semantics.
- [x] 5.3 Give the mobile exam workspace manual-save parity, safe-area spacing, landscape/zoom resilience, and reachable sheet controls.
- [x] 5.4 Associate options with the question heading, move focus on question change, scope shortcuts away from controls/overlays, and expose navigator answered/current state.
- [x] 5.5 Announce save/offline/conflict/automatic-submit transitions without timer noise.
- [x] 5.6 Add unit/component tests for offline-to-online recovery, same-tab reload, page lifecycle, navigation warning, shortcut scope, focus flow, live status, and mobile parity.

## 6. Browser Journeys And Deterministic Gates

- [x] 6.1 Cap Vitest workers at four and prove the full frontend suite passes repeatedly without the prior async flakes.
- [x] 6.2 Extend the disposable Compose browser gate with admin workspace through publish/invitation/monitoring and candidate login/start/answer/autosave/reload/submit/result.
- [x] 6.3 Add one interruption or revision-conflict browser journey and assert no browser console or server errors.
- [x] 6.4 Add controlled mobile Chromium coverage for the formal exam action area while retaining real Safari/phone checks as external UAT evidence.

## 7. Documentation Truth

- [x] 7.1 Replace normative `192.168.2.34` deployment references with `<FORMAL_LAN_IP>` and label historical/synthetic addresses explicitly.
- [x] 7.2 Document the workspace route, session-scoped recovery guarantee, closed-tab limitation, and the separation from formal Mac/Windows acceptance.

## 8. Final Verification

- [x] 8.1 Pass backend format, Ruff, ty, ordinary pytest, and the full PostgreSQL test script with no unexpected skips.
- [x] 8.2 Pass frontend format, deterministic Vitest, lint, build, offline checks, and focused browser gates.
- [x] 8.3 Pass `openspec validate --all --strict --no-interactive`, Compose configuration validation, and `git diff --check`.
- [x] 8.4 Reconcile every completed checkbox with implementation evidence and leave formal host-only tasks explicitly outside this change.
