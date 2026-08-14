## Why

The first-phase business loop is implemented, but a real exam can still be derailed by recoverable network/query failures, an interrupted candidate tab, fragmented administrator actions, or a race between starting and archiving an exam. The next iteration should make the existing workflow reliable and self-explanatory before adding broader product scope.

## What Changes

- Add an admin-only, aggregate single-exam workspace that shows publication readiness, roster/invitation/attendance/attempt/incident summaries, and one advisory next action without exposing roster PII.
- Make candidate and admin query failures recoverable, distinguish stale cached data from a successful refresh, and provide a user-triggered recovery path for lazy-route chunk failures.
- Strengthen candidate exam interruption recovery within the current session-scoped model: immediate offline status, same-tab draft recovery, background/page-exit persistence, guarded navigation, automatic retry, mobile manual-save parity, and accessible status announcements.
- Improve exam-taking keyboard, screen-reader, responsive, safe-area, zoom, and reduced-motion behavior while preserving the Academic Editorial design system.
- Serialize attempt start and exam archive decisions so an archive that completes cannot be followed by a newly created attempt, and reject archiving while attempts remain in progress.
- Add focused PostgreSQL, API, frontend, and disposable-browser coverage for the new reliability contracts.
- Correct normative deployment documentation to use `<FORMAL_LAN_IP>` while keeping formal Mac and future Windows commissioning evidence in their existing OpenSpec changes.

Non-goals: Redis, Celery, queues, LMS features, complex RBAC, full anti-cheat/monitoring, high availability, a new frontend stack, persistent offline credentials, or completing formal host commissioning in this change.

## Capabilities

### New Capabilities

- `admin-exam-workspace`: Admin-only aggregate lifecycle visibility and advisory next-action guidance for one exam.

### Modified Capabilities

- `frontend-page-experience`: Recoverable query and route failures, stale-data disclosure, interruption-safe candidate drafting, accessible focus/shortcut/status behavior, and mobile safe-area parity.
- `exam-delivery`: Shared serialization and in-progress guards for attempt start versus exam archive transitions.

## Impact

- Backend: new Pydantic workspace schemas, thin admin route, aggregate service queries, and stricter exam lifecycle locking/audit behavior.
- Frontend: new admin exam workspace route/page/API client, shared recoverable page states, route error recovery, and focused exam-taking hooks/components.
- Tests and operations: PostgreSQL concurrency coverage, API/component/browser journeys, deterministic frontend worker settings, and normative IP documentation cleanup.
- No new service, database table, migration, public port, or external dependency is required.
