## Context

The platform already runs as a single-host Docker Compose stack with PostgreSQL, a FastAPI backend, an independent auto-submit worker, a React frontend, Nginx, and a shared `learning_media` volume. The formal exam loop, candidate email OTP login, video learning, reports, and full quality gates are implemented.

The remaining risk is operational rather than business-functional. Root environment examples document SMTP, OTP, import, and other settings that Compose does not fully pass into containers. The only strict deployment tier is `production`, which correctly requires HTTPS, while the intended near-term deployment is a controlled LAN with HTTP only. `/api/health` does not check dependencies, the worker has no health signal, and backup guidance does not prove that PostgreSQL and media can be restored together.

This change targets a small number of formal internal exams on one controlled host. Candidate and admin bearer tokens remain exposed to LAN transport risk because TLS is not available; that risk is accepted only for a restricted network and must remain explicit.

## Goals / Non-Goals

**Goals:**

- Add a fail-closed `internal` deployment tier for controlled-LAN HTTP without weakening the existing production HTTPS contract.
- Make runtime configuration explicit, complete, and role-scoped for backend and worker containers.
- Expose dependency-aware backend readiness and an observable auto-submit worker heartbeat.
- Improve post-commit OTP delivery resilience with bounded retry and redacted logs.
- Produce paired PostgreSQL/media backups and verify them in an isolated restore target.
- Define automated and human gates for releasing the stack for a formal internal exam.
- Preserve development behavior and avoid database schema changes.

**Non-Goals:**

- Adding TLS certificates, certificate automation, or a new ingress product.
- Adding Redis, Celery, a durable mail queue, Prometheus, or another service.
- Adding multi-instance high availability, complex RBAC, SSO, monitoring dashboards, or LMS features.
- Changing exam snapshot, paper selection, scoring, retake, report, practice privacy, or video completion semantics.
- Automating destructive restore into the current formal deployment.

## Decisions

### 1. Add explicit runtime mode and role dimensions

`ENVIRONMENT` will support `development`, `internal`, and `production`. A separate `APP_ROLE` will distinguish `backend` and `worker` validation.

- `development` keeps current local defaults and memory email delivery.
- `internal` requires non-sample admin/token/database credentials, SMTP delivery, exact CORS origins, and an explicit private LAN bind address. It permits only controlled-LAN HTTP origins; wildcard, localhost, loopback, and any-address origins remain invalid for this tier.
- `production` keeps the current HTTPS-only CORS requirement and fail-closed secret/SMTP validation.
- The backend role validates web, auth, SMTP, import, rate-limit, and media settings.
- The worker role validates only its database and runtime inputs, so it does not receive unrelated SMTP or administrator secrets.

This separates deployment security from process responsibility. Passing every backend secret to the worker would be simpler but unnecessarily expands the worker's secret exposure. Relaxing `production` to allow HTTP was rejected because it would make an unsafe transport look production-safe.

### 2. Keep Compose as the single deployment contract

`docker-compose.yml` remains the only runtime topology. It will explicitly propagate all supported backend settings from the root environment file, including token TTL, public rate limits, OTP controls, SMTP, import limits, and media limits. The worker receives only `ENVIRONMENT`, `APP_ROLE`, `DATABASE_URL`, and worker-specific health inputs.

The Nginx host mapping will use an explicit LAN bind variable for internal deployment. Development remains backward compatible through a documented default, while internal preflight rejects an omitted, loopback, public, or any-address bind value. PostgreSQL and the direct frontend port remain loopback-only.

A separate `internal` tier was chosen over overloading `development`, because formal operation needs strict secrets and SMTP even when HTTPS is unavailable.

### 3. Separate liveness from readiness

`GET /api/health` remains a shallow liveness endpoint. `GET /api/ready` will return success only when the backend can execute a trivial database query and the configured learning media directory exists with required access. Dependency failures return HTTP 503 with a generic response that contains no credentials or filesystem details.

The backend Compose healthcheck will call readiness from inside the container. Nginx can depend on a healthy backend for startup ordering. Treating media failure as not-ready is intentionally conservative because the deployed product advertises video learning as part of the same stack.

### 4. Use a local heartbeat for the auto-submit worker

The worker will update a heartbeat file after each successful database scan, including scans with no due attempts. A healthcheck will mark the worker unhealthy when that heartbeat is absent or older than a bounded multiple of the scan interval. Failed scans do not refresh the heartbeat.

No heartbeat table or monitoring service is added. The file resets on container recreation, and the worker's immediate first scan recreates it. Existing `FOR UPDATE SKIP LOCKED`, attempt status checks, and `ends_at` semantics remain the source of idempotency and catch-up behavior.

### 5. Retry OTP delivery without adding a queue

The login challenge remains committed before SMTP delivery begins, and the request continues returning the same response shape for valid and unknown identities. The background delivery function will retry only a small bounded number of transient SMTP/network failures with short backoff. Permanent failures stop immediately.

SMTP transport is explicit and mutually exclusive: STARTTLS uses a plain SMTP connection followed by `starttls`, while implicit SSL uses `SMTP_SSL` from connection establishment. Formal profiles require one encrypted transport, and authenticated SMTP requires username and password to be configured together. This supports internal mail servers on provider-specific implicit SSL ports such as `994` without weakening the existing STARTTLS path.

Structured delivery logs will contain an event name, challenge identifier, attempt number, and exception class, but never the OTP, recipient email, SMTP password, or full submitted identity. A final failure does not roll back the challenge or produce a differentiated HTTP response; the candidate can request a replacement challenge after the cooldown.

A durable outbox was rejected because it would require a new delivery worker or queue-like subsystem outside the lightweight first-phase boundary.

### 6. Back up PostgreSQL and media as one release artifact

Backup tooling will run only during a documented maintenance window with no in-progress exams or video uploads. Each completed backup directory contains a PostgreSQL custom-format dump, a `learning_media` archive, a manifest, checksums, and a success marker written last. A partial run never produces the success marker.

Restore verification will refuse the current Compose project and restore only into a disposable database and temporary media volume. It will verify dump restoration, migration head, representative table counts, media archive integrity, and sampled file readability. The project will document recovery commands but will not provide a default command that overwrites current formal data.

Using database-only backup was rejected because restored video metadata without media files is unusable. Always-online cross-resource snapshots were rejected as unnecessary for a small single-host deployment; a maintenance window gives a simpler consistency boundary.

### 7. Release through staged evidence

Implementation will be released in three stages:

1. Configuration propagation, internal validation, readiness, and worker health.
2. Paired backup tooling and isolated restore verification.
3. Production-like internal UAT using real SMTP through the deployed Nginx entry.

Release evidence must include the existing backend/frontend/OpenSpec/Compose gates, healthy services, real OTP delivery, the formal exam/retake/report flow, worker interruption and catch-up, and a verified backup restore.

## Risks / Trade-offs

- **[LAN HTTP exposes bearer tokens to transport interception]** → Restrict the bind IP and host firewall to the controlled subnet, document the residual risk, and prohibit this mode on guest Wi-Fi, public networks, or uncontrolled segments. Move to HTTPS before expanding exposure.
- **[Role-aware validation adds configuration branches]** → Cover the full `environment × role` matrix and keep development defaults backward compatible.
- **[Background SMTP retry is not durable across backend restart]** → Keep retries short and bounded, retain resend semantics, and log final failures; do not claim queue-grade delivery.
- **[Conservative media readiness can make exam APIs unavailable when only media storage fails]** → Prefer a clear whole-stack failure before formal use; operators can restore the mounted volume and readiness without data migration.
- **[Heartbeat file is local and resets with the worker container]** → Run the first scan immediately and treat the worker as starting until the first successful heartbeat.
- **[Maintenance-window backup causes brief downtime]** → Schedule it outside exams and uploads; the simpler consistency model is acceptable for low-frequency internal operation.
- **[Restore verification uses additional temporary storage and containers]** → Make cleanup explicit and isolate it by project name and temporary volumes.

## Migration Plan

1. Add new environment fields with development-compatible defaults and role-specific validation tests.
2. Update environment examples and Compose mappings; render and test development and internal configurations without printing secret values.
3. Add readiness and worker healthchecks, then verify container startup and failure transitions.
4. Add SMTP retry/logging tests and preserve the existing uniform login response tests.
5. Add backup and restore-verification tooling and prove it against disposable resources.
6. Update the official UAT, README, and handoff documentation.
7. Before formal rollout, create a current backup, deploy the new image/configuration, wait for healthy services, and run the internal UAT.

Rollback restores the previous Compose file, image, and environment configuration. No database downgrade is expected because this design adds no schema migration. Existing `development` deployments remain valid throughout.

## Open Questions

None. The target is a controlled LAN without current HTTPS capability, the residual HTTP risk is explicitly accepted, and the scope is limited to single-host formal internal use.
