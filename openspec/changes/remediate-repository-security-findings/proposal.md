## Why

The repository-wide security scan at `665a5bf6a2d42e67c0f10f687108957fab2ffa37` identified fifteen reachable configuration, parsing, resource, archival, release, and proxy weaknesses. They must be closed before the next formal internal release without expanding the first-phase architecture or weakening the controlled-LAN operating boundary.

## What Changes

- Fail closed on unsafe formal credentials, token lifetimes, malformed signed-token fields, destructive account migrations, destructive PostgreSQL test targets, and unsupported scanner severities.
- **BREAKING** Require formal `TOKEN_SECRET` values to be canonical unpadded Base64url encodings of exactly 32 random bytes; the rollout rotates the secret and invalidates existing sessions, OTP challenges, and registration credentials.
- **BREAKING** Stop restoring administrator, attempt-session, and attempt-draft state from legacy `localStorage`; old persistent browser state is purged and users must authenticate again.
- Bound practice submissions and wrong-question reads, preserve all-time mastery/counts in an aggregate table, and add guarded archival deletion for old practice-answer details.
- Inspect XLSX ZIP metadata before `openpyxl`, preserve frozen roster identity in schema-v2 lifecycle archives, and escape every untrusted XLSX cell.
- Authenticate sealed macOS release bundles with offline RSA-3072 signatures and external pinned public-key fingerprints.
- Replace spoofable forwarded-header trust with Nginx overwrite semantics and exact static gateway peer allowlists.
- Add regression tests, deployment contracts, operations guidance, and a clean-HEAD security re-scan gate for all fifteen findings.

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
- `internal-deployment-readiness`: Makes scanner severity fail closed, authenticates macOS release bundles, and restricts proxy-header trust to the two configured gateways.

## Impact

- Backend settings, token helpers, practice models/services/schemas/routes, Alembic revisions, retention/import services, operations APIs, backup fingerprints, and focused tests.
- Frontend session helpers, practice API types, wrong-question pagination, error handling, and tests.
- Docker Compose networking, Nginx headers, CI/test database environment contracts, macOS release scripts, environment examples, and operations documentation.
- One additive practice aggregate migration plus a guarded maintenance workflow; no new runtime dependency or external service.
