## Why

The first-phase exam loop is complete, but the current Docker Compose deployment cannot safely represent a real internal rollout: documented OTP/SMTP and import settings are not fully passed into containers, LAN HTTP has no explicit hardened runtime profile, and readiness, worker health, and paired database/media recovery are not proven. These gaps should be closed before the platform is used for formal internal exams.

## What Changes

- Add an explicit `internal` runtime mode for formal use on a controlled LAN while keeping `production` fail-closed on HTTPS requirements.
- Introduce role-aware runtime validation so the backend receives and validates auth, SMTP, import, media, and security settings while the auto-submit worker receives only the settings it needs.
- Make Docker Compose pass through every supported runtime setting and require an explicit LAN bind address for internal deployment preflight.
- Keep `/api/health` as liveness and add dependency-aware readiness plus Compose health checks for the backend and auto-submit worker.
- Add STARTTLS and implicit SSL SMTP transports, bounded retry, and redacted structured logging for post-commit OTP email delivery without changing the uniform candidate-login response contract.
- Preserve auto-submit idempotency and require overdue attempts to be processed after a worker interruption, with an observable worker heartbeat.
- Add paired PostgreSQL and `learning_media` backup artifacts, checksums, and isolated restore verification that cannot target current formal data by default.
- Extend the official UAT and handoff gates so a real SMTP login, formal exam flow, worker recovery, and backup restore must pass before internal release.

## Non-goals

- HTTPS certificate issuance or TLS termination inside this project.
- Redis, Celery, message queues, Prometheus, or a new monitoring stack.
- Multi-instance high availability, complex RBAC, multi-tenancy, SSO, proctoring, or broader LMS features.
- Changes to exam snapshot, fixed-paper, scoring, retake, practice privacy, or video-learning business semantics.

## OpenSpec ownership and archive order

This completed baseline remains an active change for this round and MUST NOT be auto-archived here. It owns the generic controlled-LAN runtime, readiness, worker health, and paired-restore baseline only. `support-macos-formal-host-portability` owns the selected macOS formal-host acceptance and portability details, while `stabilize-windows-internal-exam-platform` owns the future Windows Docker Desktop + WSL2 acceptance track. Archive these changes separately and in evidence order: leave harden active this round, archive support only after real Mac acceptance, and archive stabilize only after real Windows staging, cutover, UAT, and evidence complete. A later archive MUST preserve the other active change's capability ownership rather than overwriting or absorbing its host-specific specs.

## Capabilities

### New Capabilities

- `internal-deployment-readiness`: Defines the controlled-LAN runtime profile, configuration propagation, readiness and worker health, paired backup/restore verification, and internal release gates.

### Modified Capabilities

- `admin-security`: Extends safe startup validation to the explicit internal runtime mode and separates backend and worker configuration responsibilities.
- `candidate-access`: Adds bounded, non-leaking OTP email delivery retry and operational failure logging while preserving the uniform challenge response.
- `exam-delivery`: Requires the auto-submit worker to expose health and catch up overdue attempts safely after interruption without duplicating submissions.

## Impact

- Backend configuration, app startup, health endpoints, email delivery, auto-submit worker, schemas, and related tests.
- `docker-compose.yml`, root/backend environment examples, Nginx bind configuration, and deployment configuration tests.
- Backup and isolated restore-verification tooling for PostgreSQL and the `learning_media` volume.
- `README.md`, `docs/official-exam-uat-checklist.md`, `docs/handoff.md`, and deployment/operations guidance.
- Adds `/api/ready`; no new external service, package, or database schema is expected.
