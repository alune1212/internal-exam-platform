## Why

The repository-wide security scan at `665a5bf6a2d42e67c0f10f687108957fab2ffa37` identified fifteen reachable configuration, parsing, resource, archival, release, and proxy weaknesses. The implementation review also found separate tracked-workbook metadata, invitation-limiter, learning-media, CI Docker-socket, and macOS scanner-evidence paths. They must be closed before the next formal internal release without expanding the first-phase architecture or weakening the controlled-LAN operating boundary.

## What Changes

- Fail closed on unsafe formal credentials, token lifetimes, malformed signed-token fields, destructive account migrations, destructive PostgreSQL test targets, and unsupported scanner severities.
- **BREAKING** Require formal `TOKEN_SECRET` values to be canonical unpadded Base64url encodings of exactly 32 random bytes; the rollout rotates the secret and invalidates existing sessions, OTP challenges, and registration credentials.
- **BREAKING** Stop restoring administrator, attempt-session, and attempt-draft state from legacy `localStorage`; old persistent browser state is purged and users must authenticate again.
- Bound practice submissions and wrong-question reads, preserve all-time mastery/counts in an aggregate table, and add guarded archival deletion for old practice-answer details.
- Inspect XLSX ZIP metadata before `openpyxl`, preserve frozen roster identity in schema-v2 lifecycle archives, and escape every untrusted XLSX cell.
- Authenticate sealed macOS release bundles with offline RSA-3072 signatures and external pinned public-key fingerprints.
- Replace spoofable forwarded-header trust with Nginx overwrite semantics and exact static gateway peer allowlists.
- Remove local metadata from the tracked question-bank workbook, bound invitation limiter state atomically, and keep retention backup IDs beneath the configured root.
- Replace public learning-media aliases with short-lived candidate/video-bound playback URLs that recheck current lifecycle state.
- Remove the host Docker socket and Docker CLI from PR-controlled browser tests, and bind macOS release reports to retained raw scanner evidence that trusted code recomputes.
- Bound candidate exam answer-save payloads and XLSX logical worksheet dimensions, paginate and rate-limit the practice catalog, isolate checkout credentials in every pull-request job, and release the backup freeze after ordinary post-acquisition failures.
- Add regression tests, deployment contracts, operations guidance, and a clean-HEAD security re-scan gate for the fifteen original findings plus separately tracked implementation-review findings.

## Non-goals

- Redis, Celery, queues, microservices, complex RBAC, a new monitoring stack, or a separate practice service.
- HTTPS automation, LMS expansion, Word imports, proctoring, or changes to exam snapshot, fixed-paper, scoring, invitation, or result-release semantics.
- Treating macOS evidence as completion of the pending native Windows acceptance tasks.

## Capabilities

### New Capabilities

- `data-lifecycle`: Defines reconstructable schema-versioned exam and practice archives, paired-backup deletion safeguards, and formula-safe operator workbooks.

### Modified Capabilities

- `admin-security`: Strengthens formal credential/session configuration, token parsing, legacy browser-state cleanup, destructive migration gates, and safe PostgreSQL test targeting.
- `candidate-access`: Bounds practice writes and wrong-question reads while retaining all-time mastery/count semantics and guarded access to archived detail.
- `admin-imports`: Rejects oversized or malformed XLSX archives before workbook expansion.
- `exam-invitations`: Keeps public invitation limiter state bounded and atomic after validating the target exam.
- `internal-deployment-readiness`: Makes scanner severity fail closed, authenticates macOS release bundles, and restricts proxy-header trust to the two configured gateways.
- `video-learning`: Requires authorized, revocable candidate playback instead of a public static media alias.

## Impact

- Backend settings, token helpers, practice models/services/schemas/routes, Alembic revisions, retention/import services, operations APIs, backup fingerprints, and focused tests.
- Frontend session helpers, practice API types, wrong-question pagination, error handling, and tests.
- Docker Compose networking and media mounts, Nginx headers, CI/test database environment contracts, macOS release scripts/evidence, environment examples, and operations documentation.
- One additive practice aggregate migration plus a guarded maintenance workflow; no new runtime dependency or external service.
