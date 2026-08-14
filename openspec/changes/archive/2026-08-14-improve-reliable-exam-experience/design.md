## Context

See `proposal.md` for motivation. The current application already has persisted attempt snapshots, session-scoped draft storage, optimistic answer revisions, one-in-progress-attempt uniqueness, invitation claims, publication readiness, result-release gates, and an Academic Editorial component system. The reliability gap is primarily coordination: lifecycle state is spread across pages, recoverable query failures lack consistent actions, browser lifecycle events are only partly handled, and `start_exam` reads active state before joining the transaction mutex used by archive mutations.

The formal Mac commissioning and future Windows cutover changes remain separate sources of truth. This change must remain deployable on the existing six-service Compose topology without a schema migration or new service.

## Goals / Non-Goals

**Goals:**

- Give an administrator one privacy-bounded, exam-scoped operational view and one advisory next action.
- Make browser and network interruption states explicit and recoverable within the existing tab session.
- Close the start-versus-archive transaction race without weakening fixed-paper, snapshot, writer-fence, or retake invariants.
- Add deterministic automated evidence at service, HTTP, component, and browser boundaries.

**Non-Goals:**

- Replacing existing edit, roster, invitation, incident, or report pages with a new workflow engine.
- Durable offline examination, cross-device draft synchronization, persistent browser credentials, or background sync service workers.
- New infrastructure, database tables, queues, LMS/anti-cheat scope, or completion of host commissioning evidence.

## Decisions

### 1. Add one aggregate read model rather than composing row APIs in the browser

Add `GET /api/admin/exams/{exam_id}/workspace`, a Pydantic `ExamWorkspaceRead` family, and a dedicated backend service. The route remains thin and inherits the existing admin router dependency. The service captures one UTC `observed_at`, loads the exam, computes draft readiness only for draft status, and uses grouped/windowed SQL for account, invitation, latest-attempt attendance, raw attempt, void, and unused-retake counts.

The response contains no roster rows or identity fields. Latest attendance follows the established report rule: greatest `(attempt_no, id)` per scope, submitted plus auto-submitted are submitted, and latest voided is not started. Raw attempt counts remain separate so release/incident decisions do not lose history.

Alternative considered: call exam list, invitation status, candidate list, and report endpoints from the page. Rejected because it multiplies requests, reuses an N+1 row path, exposes unnecessary PII, and can derive contradictory counts while the invitation worker changes state.

### 2. Derive one advisory next action on the server

The backend derives a bounded enum using explicit precedence: draft roster/readiness; invitation in-flight, unsent, then failed; not-yet-open; in-progress/open monitoring; incident review; result release; archive; complete. The frontend renders the reason and deep-links to existing mutation pages. Every mutation endpoint remains authoritative and rechecks state.

Alternative considered: duplicate lifecycle rules in React. Rejected because API and UI rules would drift and other admin clients could not reuse the same explanation.

### 3. Keep workspace refresh bounded and query-owned

The workspace query refreshes every fifteen seconds only while the returned exam is active. Draft changes rely on mutation invalidation; archived workspaces do not poll. Existing invitation-detail polling is reduced to a short interval only while a delivery claim is in flight. All successful exam-scoped mutations invalidate the workspace query key.

Alternative considered: WebSockets or server-sent events. Rejected as unnecessary infrastructure for a single-host internal tool.

### 4. Use shared recoverable page states and a route error boundary

Extend existing `PageState` composition patterns so first-load errors expose retry/safe navigation, while background refresh failures keep cached data and show a stale warning with the last successful update time. Authentication failures continue through the centralized session-clearing path. A route-level error element catches lazy-module failure and offers user-triggered reload/home actions; it never automatically loops.

This is an incremental page migration, beginning with exam, practice, learning, result, report, account, operations, and the new workspace surfaces identified by tests. It preserves local UI primitives and copy helpers.

### 5. Extend the draft queue without broadening storage scope

Continue writing every answer change synchronously to the existing attempt-scoped `sessionStorage` draft, then debounce server saves. Add `offline`, `visibilitychange`, `pagehide`, and guarded `beforeunload` handling. Hidden/page-exit paths persist synchronously and attempt ordinary best-effort synchronization when the document is still permitted to issue it; visible/online paths retry the serialized save queue. No credential or draft moves to `localStorage`, IndexedDB, or a service worker.

The queue exposes whether unsynchronized work exists so the page can guard navigation and give mobile users the same explicit save action as desktop. Revision conflicts remain terminal until the existing retry/takeover UI resolves them; submission still performs a full save and is not duplicated.

Alternative considered: `sendBeacon`. Rejected because the answer-save endpoint requires custom candidate and attempt-session headers plus revisioned JSON semantics that cannot be safely weakened for unload delivery.

### 6. Scope keyboard behavior to the exam workspace

Question headings become programmatically focusable and option groups reference them. On question change, focus moves to the heading. Shortcuts run only from the focus workspace and ignore interactive elements, dialogs, sheets, and modifier-key combinations. Navigator items expose current/answered/unanswered state, and a concise live region announces save/offline/conflict/automatic-submit transitions without reading every countdown tick.

Desktop and mobile continue to share existing focus components; the mobile branch receives manual save parity, safe-area padding, and viewport/zoom regression coverage rather than a visual redesign.

### 7. Acquire the lifecycle mutex before deciding to create a new attempt

Preserve the existing read-only resume path for an already in-progress attempt, including while a writer fence or backup freeze blocks mutations. When no attempt can be resumed, join the shared transaction mutex, load the exam with a row lock, and re-evaluate active status before applying timing, retake, and paper rules in the same transaction. Any status-changing admin update also row-locks the exam. The existing admin mutation guard holds the same transaction mutex and counts in-progress attempts, so ordering becomes deterministic:

- archive first: start reloads archived and rejects;
- start first: archive waits, then observes in-progress and rejects.

The partial unique index and existing integrity-error normalization remain the final defense for start-versus-start. A real PostgreSQL race test proves both orderings; SQLite tests continue to cover ordinary behavior.

### 8. Keep lifecycle mutations and their audit event atomic

The admin exam update route executes the service mutation without committing, records an allowlisted `exam_updated` audit event including `from_status` and `to_status`, and commits once. Publish retains its specialized event. A failed mutation or failed audit rolls back both. This ensures an archive suggested by the workspace is traceable without introducing a new archive endpoint.

### 9. Treat deterministic tests and deployment wording as release hygiene

Configure frontend Vitest to cap workers at four, matching the stable live run, and add focused tests before full gates. Normative deployment documents replace hard-coded historical IP values with `<FORMAL_LAN_IP>`; historical evidence remains explicitly labelled. These edits do not claim formal host acceptance.

## Risks / Trade-offs

- [Aggregate counts can change immediately after `observed_at`] → Display the timestamp, poll only while useful, and keep next actions advisory with mutation-time revalidation.
- [A page-exit HTTP save is not guaranteed by browsers] → Persist the latest snapshot synchronously in tab-scoped storage and state the closed-session limitation explicitly.
- [Row locking can increase start/archive latency] → Reuse the existing transaction mutex, keep the critical transaction bounded, and verify contention with PostgreSQL race tests.
- [A global navigation warning can annoy candidates] → Enable it only for an active attempt with unsynchronized work and remove it after successful save or terminal submission.
- [A broad query-state migration can create visual inconsistency] → Reuse `PageState`, `Alert`, `Button`, and existing Academic Editorial tokens; add focused tests instead of new page-specific patterns.
- [Server-derived next action may be temporarily stale] → Return `observed_at`, invalidate after mutations, and never use the action as authorization.

## Migration Plan

1. Land backend schemas/service/route and locking changes with unit, HTTP, and PostgreSQL concurrency tests; no Alembic revision is needed.
2. Land frontend API/types/workspace and shared recovery primitives behind existing admin/candidate authentication.
3. Migrate the named high-risk pages, add browser journeys, and correct normative IP documentation.
4. Run backend full PostgreSQL, frontend deterministic, disposable Compose browser, OpenSpec strict, and diff hygiene gates.
5. Roll back by reverting application code; persisted exam, attempt, invitation, and audit data remain compatible because no schema or stored contract is removed.
