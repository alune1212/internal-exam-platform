## Why

> **Target update (2026-08-07):** `support-macos-formal-host-portability` selects macOS as the current formal target/source. This change now preserves the Windows Docker Desktop + WSL2 adapter and its real-host acceptance track for a future Mac-to-Windows migration; macOS evidence does not complete the remaining Windows tasks or make either host ready without its own acceptance gates.

The business loop and first internal-deployment hardening are complete, and the current selected formal source/target is macOS; real Mac host acceptance remains a separate pending gate. This change preserves the Windows Docker Desktop + WSL2 adapter, its application hardening, and a future native AMD64 cutover acceptance track; Windows is not the active formal writer or a ready host until that track completes. The platform still needs a reproducible Windows operations contract, compensating controls for an explicitly accepted shared-office-LAN HTTP exception, stronger exam incident handling, and a small set of learning and lifecycle improvements before Windows can become the stable internal instance.

## What Changes

- Add a Docker Desktop + WSL2 Windows deployment contract delivered as a versioned, checksummed release bundle with PowerShell-only host operations, pinned image digests, same-host disposable staging, automated preflight, restart/log rotation, diagnostics, and backup-based rollback.
- Preserve an executable Mac-to-Windows cutover contract: restore the final Mac paired backup into native Linux AMD64 Windows staging, verify `datasetId`/`hostId`/`writerGeneration` and the cutover manifest, stop the entire Mac formal project, and accept Windows as the sole writer only after target gates pass.
- **BREAKING** Split the public candidate LAN entry from the loopback-only admin/operations entry. LAN clients cannot reach admin pages, admin APIs, readiness details, or OpenAPI documentation.
- Keep `internal` HTTP as an explicitly accepted shared-office-LAN exception, limit administrator use to the host, cap admin and candidate tokens at four hours, cap formal exams at two hours, and add a safe close-exam operation that invalidates all sessions.
- Replace the single shared administrator identity with two named, equal-permission operators while allowing only one active operator mode at a time: backup disabled means primary-only, backup enabled means backup-only with immediate invalidation of primary credentials and existing tokens, and switching back invalidates backup credentials and tokens; keep backup disabled by default and persist a non-secret administrative audit trail.
- Add publication readiness checks and typed confirmation, a 30-minute early-login window, a 15-minute start grace period with full duration, single-active-device exam ownership, browser-local pending-answer recovery, and automatic admin mutation gates during in-progress attempts.
- Default candidate results to score/pass only, keep ranking admin-only, and allow answers and analysis to be released once, after all attempts are terminal.
- Add incident-safe voided attempts, audited bulk retake grants, per-exam evidence bundles, and recovery rules that pause or reschedule rather than add high availability or global timer suspension.
- **BREAKING** Change practice from blind submission to immediate correctness, correct-answer, and analysis feedback for the shared question bank; lock each submitted practice answer and add a lightweight wrong-question review flow.
- Add twelve-month online data retention with previewed operator-confirmed archival deletion, daily opportunistic paired backup with a short write freeze, encrypted second-copy retention, restore drills, and disk reserve enforcement.
- Make the frontend runtime independent of third-party fonts/CDNs, define supported browser and accessibility gates, add core browser E2E coverage, and perform behavior-preserving decomposition of the oversized exam service and taking page.
- Add scheduled dependency/image security scanning and retain the lightweight single-host, no-queue, no-proctoring architecture.

## Non-goals

- HTTPS, certificate distribution, domain acquisition, network segmentation, or treating the accepted HTTP exception as equivalent to encrypted transport.
- Redis, Celery, durable SMTP queues, microservices, multi-host high availability, automatic failover, or uninterrupted continuation after host failure.
- Complex RBAC, multi-tenancy, SSO, a full monitoring stack, 24×7 operator response, or a full anti-cheat/proctoring suite.
- Global exam timer suspension, manual OTP bypass, administrator score editing, Word import, or broader LMS/course-management behavior.
- Separate formal and practice question banks; practice feedback intentionally covers the shared active bank.

## OpenSpec ownership and archive order

There are three active change directories. `harden-internal-deployment-readiness` is a completed baseline but is intentionally not auto-archived in this round; it must not reclaim host-specific capability ownership. `support-macos-formal-host-portability` owns the selected Mac formal source/target, shared portability identity, and cross-host `prepare-cutover`/`accept-cutover` contract. This change owns the implemented application hardening and future Windows adapter, while tasks 12.4 and 12.5 remain pending native AMD64 Mac-to-Windows cutover acceptance. Archive separately and in evidence order: leave harden active for this round, archive support only after real Mac acceptance, and archive this Windows change only after real Windows staging, cutover, UAT, and evidence complete 12.4/12.5 (with 12.6). Never treat Mac evidence as Windows completion or archive one change by overwriting another change's specs.

## Capabilities

### New Capabilities

- `windows-deployment-operations`: Defines the dedicated Windows Docker Desktop runtime, release packaging, local PowerShell operations, ingress split, preflight, staging, rollback, diagnostics, capacity evidence, and 24×7 best-effort service boundary.
- `data-lifecycle`: Defines twelve-month online retention, operator-confirmed archival deletion, paired backup retention and second-copy protection, opportunistic write-frozen backup, restore drills, and storage safety thresholds.

### Modified Capabilities

- `internal-deployment-readiness`: Extends formal internal readiness to the selected host and future Windows target, the explicitly accepted shared-office-LAN HTTP exception, split local/LAN exposure, session closure, evidence, and host-specific release/cutover gates.
- `admin-security`: Adds two named equal-permission operators with mutually exclusive active modes, default-disabled backup access, loopback-only administration, four-hour sessions, global close-exam revocation, and immutable audit records.
- `candidate-access`: Adds four-hour candidate sessions, early login, single-active-device exam access, fail-closed SMTP behavior, answer-revealing practice submissions, and wrong-question review.
- `exam-delivery`: Adds the two-hour duration ceiling, start grace semantics, publication preflight and confirmation, in-exam admin write protection, recoverable answer drafts, one-time result-detail release, voided attempts, and bulk retake recovery.
- `admin-imports`: Prevents import mutations during formal attempts or coordinated backup write freezes while preserving existing bounded Excel validation and failure reporting.
- `admin-reporting`: Excludes voided attempts from normal result aggregates, keeps ranking administrator-only, and reports incident/retake outcomes consistently.
- `video-learning`: Enforces disk reserve checks and coordinated write gates for uploads and video mutations without coupling learning completion to exam eligibility.
- `frontend-page-experience`: Adds supported-browser self-checks, explicit offline/save states, local pending-answer recovery, third-party-free runtime assets, lightweight accessibility gates, and core browser E2E coverage.

## Impact

- Backend configuration, authentication tokens, operator identity, audit persistence, exam publication/start/save/submit/result services, practice responses, retention and backup coordination, reports, imports, video uploads, schemas, migrations, and tests.
- Frontend routing, session handling, exam-taking state, practice and wrong-question pages, result release controls, operations/readiness views, local assets, accessibility behavior, and API clients.
- `docker-compose.yml`, Nginx ingress topology, Dockerfiles and image references, Windows PowerShell release/operations scripts, environment examples, CI/security scanning, release manifests, and Windows staging workflows.
- README, Windows deployment/operations guidance, formal exam UAT, HTTP exception documentation, retention policy, recovery runbooks, and handoff evidence.
- No Redis, queue, extra database server, external monitoring service, certificate service, or complex authorization subsystem is introduced.
