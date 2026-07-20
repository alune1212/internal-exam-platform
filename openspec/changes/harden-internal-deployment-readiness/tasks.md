## 1. Runtime Profiles And Configuration

- [x] 1.1 Add `internal` environment and backend/worker `APP_ROLE` settings with development-compatible defaults and role-specific fail-closed validation for secrets, SMTP, database credentials, CORS, and private LAN binding.
- [x] 1.2 Add backend tests for the full `development` / `internal` / `production` by `backend` / `worker` validation matrix, including non-sensitive failure messages.
- [x] 1.3 Update root/backend environment examples with the supported role, LAN bind, token TTL, rate-limit, OTP, SMTP, import, media, and worker-health fields.
- [x] 1.4 Update `docker-compose.yml` to pass all supported backend settings, keep worker secrets least-privileged, use the explicit LAN bind variable, and preserve loopback-only PostgreSQL/frontend bindings.
- [x] 1.5 Extend deployment configuration tests to assert backend overrides are propagated, worker SMTP/admin secrets are absent, internal binding is explicit, and production remains HTTPS-only.

## 2. Backend Readiness

- [x] 2.1 Add a service-layer readiness check for a trivial PostgreSQL query and required learning-media directory access without exposing dependency details or credentials.
- [x] 2.2 Add the thin `/api/ready` route and Pydantic response shape while preserving `/api/health` as shallow liveness.
- [x] 2.3 Add backend tests for ready, database-unavailable, and media-unavailable responses, including HTTP 503 and non-sensitive error content.
- [x] 2.4 Add a backend Compose healthcheck and make Nginx startup depend on backend health without changing the public `/api` or media paths.

## 3. Auto-Submit Worker Health And Recovery

- [x] 3.1 Update the worker to write an atomic local heartbeat after every successful database scan, including scans with zero due attempts, and never refresh it after failed scans.
- [x] 3.2 Add a worker healthcheck command that reports unhealthy when the heartbeat is missing or stale relative to the configured scan interval and grace period.
- [x] 3.3 Add unit tests for heartbeat creation, staleness, scan failure, and recovery, plus regression coverage that overdue attempts are caught up without resubmitting completed attempts.
- [x] 3.4 Wire the worker healthcheck and its minimal runtime settings into Docker Compose and assert its rendered environment contains no SMTP or administrator credentials.

## 4. Candidate OTP Delivery Resilience

- [x] 4.1 Add bounded short-backoff retry for transient post-commit SMTP/network failures and stop immediately for permanent delivery failures without adding a queue or new persistence model.
- [x] 4.2 Add structured delivery logs keyed by challenge id and attempt number while excluding OTPs, recipient email, submitted identity, and SMTP credentials.
- [x] 4.3 Add backend tests for first-attempt success, transient failure followed by success, exhausted retry, permanent failure, preserved challenge state, uniform HTTP response, and sensitive-log redaction.
- [x] 4.4 Support mutually exclusive SMTP STARTTLS and implicit SSL transports, validate authentication pairs, propagate the new setting, and verify real delivery on the configured port.

## 5. Paired Backup And Restore Verification

- [x] 5.1 Add maintenance-window backup tooling that writes a PostgreSQL custom-format dump and `learning_media` archive into one timestamped directory.
- [x] 5.2 Generate the backup manifest and checksums, write the success marker last, and ensure partial or checksum-failed backups are never considered valid.
- [x] 5.3 Add restore-verification tooling that refuses the current Compose project by default and restores only into disposable database/media resources.
- [x] 5.4 Verify restored migration head, representative database counts, media archive integrity, and sampled file readability, with explicit cleanup of temporary resources.
- [x] 5.5 Add safe automated tests or dry-run fixtures for backup validation, partial failure, checksum mismatch, current-target refusal, and disposable restore command construction.

## 6. Internal Operations And Documentation

- [x] 6.1 Update `README.md` with the three runtime profiles, exact internal environment checklist, Compose configuration flow, LAN HTTP residual risk, and rebuild/recreate guidance.
- [x] 6.2 Update `docs/official-exam-uat-checklist.md` with internal preflight, host firewall/LAN restrictions, real SMTP, healthchecks, worker interruption recovery, and paired restore verification.
- [x] 6.3 Update `docs/handoff.md` with the new runtime contract, operational commands, fresh validation evidence, remaining HTTP risk, and HTTPS upgrade boundary.
- [x] 6.4 Document backup creation, isolated restore verification, failure handling, and the prohibition on default restore into current formal data.

## 7. Verification And Release Gate

- [x] 7.1 Run backend format, lint, type, and full test gates: `uv run ruff format . --check`, `uv run ruff check .`, `uv run ty check`, and `uv run pytest`.
- [x] 7.2 Run frontend format, test, lint, and build gates: `npm run format:check`, `npm test -- --run`, `npm run lint`, and `npm run build`.
- [x] 7.3 Run `openspec validate --all --strict` and render both development and internal Compose configurations without printing secret values.
- [x] 7.4 Build and start the Compose stack, confirm backend and worker are healthy, run Alembic to head, validate Nginx, and verify `/api/health`, `/api/ready`, `/docs`, and media routing through `8080`.
- [ ] 7.5 Complete real-SMTP browser UAT from a second allowed LAN device through login, exam start/save/resume/submit/result, worker interruption and catch-up, retake, reports, and export.
- [x] 7.6 Create a paired backup in a maintenance window and complete isolated restore verification before marking the change ready for formal internal use.
- [x] 7.7 Perform an adversarial final review for requirement coverage, minimal scope, secret exposure, HTTP boundary, failure handling, rollback safety, and documentation accuracy.
