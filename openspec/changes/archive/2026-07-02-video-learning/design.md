## Context

The current platform has two authenticated surfaces: candidate pages protected by `X-Candidate-Token` and administrator pages protected by `X-Admin-Token`. It already separates route handlers, Pydantic schemas, service logic, SQLAlchemy models, Alembic migrations, frontend API modules, TanStack Query keys, and Academic Editorial UI primitives.

Video learning adds a new persistence-heavy feature across backend, frontend, Docker, and Nginx. The user requirement is intentionally independent from exams: uploaded learning videos must not change active exam discovery, exam start, attempt snapshots, scoring, rankings, retake grants, or existing reports. The completion rule is fixed at 90 percent of stored video duration.

## Goals / Non-Goals

**Goals:**

- Provide a standalone learning module for locally uploaded videos.
- Allow administrators to upload, publish, archive, list, and edit learning video metadata.
- Store uploaded media files on local storage using generated storage keys rather than user-provided filenames.
- Let authenticated active candidates list and watch published videos.
- Track per-candidate progress and mark completion at 90 percent watched progress.
- Provide administrator learning completion reporting and Excel export.
- Preserve all current exam, practice, auth, report, and frontend design-system contracts.

**Non-Goals:**

- No exam prerequisite gating and no change to exam eligibility.
- No course hierarchy, chapters, certifications, notifications, comments, notes, or full LMS workflow.
- No live streaming, HLS transcoding pipeline, DRM, screen-recording prevention, SCORM, xAPI, or anti-cheat suite.
- No queue worker, Redis, Celery, or background video processing.
- No complex RBAC beyond the existing administrator token and candidate token split.

## Decisions

### Decision: Model learning as a standalone capability

Create new `learning_video` and `learning_video_progress` tables instead of extending `exam`, `exam_attempt`, or `practice_answer`.

Rationale:

- The user explicitly wants learning and exams to be independent.
- Existing exam snapshot and fixed-paper semantics are sensitive; adding learning state there would create unnecessary coupling.
- Learning reports can join candidates and videos directly without affecting exam report SQL.

Alternative considered: attach videos to exams. Rejected because it would imply prerequisite or exam-scoped semantics and create pressure to modify active exam listing and start rules.

### Decision: Use local uploaded media with generated storage keys

The admin upload flow should receive files with FastAPI `UploadFile`, validate metadata and file bounds, write to a configured local storage directory, and persist only generated storage keys plus display metadata.

Rationale:

- `UploadFile` avoids treating video uploads as in-memory byte payloads.
- Server-generated keys avoid path traversal and user filename exposure in storage paths.
- Local storage fits the requested first-phase implementation better than object storage or CDN.

Alternative considered: storing video bytes in PostgreSQL. Rejected because it would bloat database backups and make streaming inefficient.

### Decision: Let Nginx/static media serving handle video bytes

The backend should own upload validation, metadata, auth-gated API responses, and progress writes. Uploaded video byte delivery should be served from a configured media path through Nginx or static file serving, not proxied through ordinary JSON API handlers.

Rationale:

- Video playback depends on byte range behavior and large-file delivery.
- The existing Compose/Nginx entrypoint is already the browser-facing path.
- Keeping media delivery outside service-layer business logic reduces FastAPI worker pressure.

Trade-off:

- Native `<video>` requests cannot attach `X-Candidate-Token` headers. The first phase should expose opaque generated media paths only through token-gated APIs and document that direct shared media URLs are not DRM. If content sensitivity expands, move to signed URLs, Nginx `auth_request`, or object storage signed URLs.

### Decision: Store duration at upload time without adding a transcoding dependency

The upload request should include `duration_seconds`, populated by the admin browser from video metadata before upload and validated server-side as a positive bounded number. The stored duration is the basis for the 90 percent completion threshold.

Rationale:

- Reliable server-side probing would add `ffprobe` or another media dependency and complicate Docker packaging.
- The current project favors lightweight internal-tool scope.
- Administrators are trusted users in this phase.

Alternative considered: add media probing/transcoding. Rejected for the first phase; it can be a later hardening step if uploaded media quality or metadata trust becomes a real issue.

### Decision: Track watched intervals, not only the latest position

Progress updates should persist a compact representation of watched intervals per candidate/video and merge overlapping intervals before calculating watched seconds and completion percentage.

Rationale:

- `currentTime >= 90%` can be faked by seeking near the end.
- Interval merging prevents repeated views of the same segment from double-counting.
- This gives a practical internal-tool completion signal without pretending to be anti-cheat.

Alternative considered: store only `last_position_seconds`. Rejected because it cannot distinguish watched content from a seek jump.

### Decision: Keep reports separate from existing exam reports

Create learning report endpoints and frontend pages under the learning capability instead of modifying score, accuracy, wrong-question, absent-candidate, or ranking reports.

Rationale:

- Learning completion is not an exam result.
- Existing admin report specs are exam-oriented and should remain stable.
- A separate report avoids ambiguous filtering semantics between exam IDs and videos.

### Decision: Use first-phase operational defaults

Use configurable upload limits with a first-phase default of 500 MiB, hide archived videos from all candidate-facing learning pages, retain progress data for archived videos in administrator reports, and include Excel export in the first implementation.

Rationale:

- A default limit keeps Nginx, backend, and frontend behavior concrete while still allowing deployment override.
- Hiding archived videos gives administrators a simple removal control without deleting audit history.
- Including export now matches existing administrator report patterns and avoids a partial reporting surface.

## Risks / Trade-offs

- [Risk] Uploaded video URLs may be shareable if media is served as static files. -> Mitigation: use opaque generated storage keys, expose URLs only through token-gated APIs, document the limitation, and leave signed URLs or Nginx auth as a future security upgrade.
- [Risk] Admin-provided browser-detected duration can be inaccurate. -> Mitigation: validate positive bounded duration, display stored duration in admin UI, and leave server-side media probing as a future hardening task if needed.
- [Risk] Large uploads can exceed proxy or backend limits. -> Mitigation: add a single configured max upload size and align FastAPI validation, Nginx `client_max_body_size`, Docker volume sizing, and frontend copy.
- [Risk] Progress heartbeat traffic can become noisy. -> Mitigation: send heartbeats at a modest interval, upsert one candidate/video progress row, and avoid storing unbounded raw event logs.
- [Risk] Interval JSON can grow if users seek repeatedly. -> Mitigation: merge intervals on every write and cap precision to whole seconds.
- [Risk] New navigation and pages could drift from the frontend design system. -> Mitigation: use existing `PageShell`, `PageHeader`, `PageState`, UI primitives, query keys, and auth/session patterns.

## Migration Plan

1. Add Alembic migration for `learning_video` and `learning_video_progress`.
2. Add configurable media storage settings and ensure local directories are created or validated at startup/upload time.
3. Update Docker Compose and Nginx to mount and serve the uploaded-media directory through the 8080 entrypoint.
4. Add backend schemas, models, services, and routes for admin video management, candidate video access/progress, and admin learning reports.
5. Add frontend API modules, routes, navigation entries, candidate learning pages, admin learning pages, and report/export UI.
6. Update docs for storage, upload limits, media backup, and validation commands.

Rollback strategy:

- Disable or remove learning navigation entries and routes if the feature must be hidden.
- Keep archived uploaded media files on disk until an operator confirms they are no longer needed.
- Database rollback can drop the new learning tables only if no production learning data must be retained.

## Open Questions

- None blocking for the first implementation; deployment operators may still tune the configured upload size before production use.
