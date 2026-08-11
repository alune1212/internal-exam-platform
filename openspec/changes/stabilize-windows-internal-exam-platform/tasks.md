## 1. Persistence And Core Module Boundaries

- [x] 1.1 Add regression tests that lock current snapshot, frozen-pool, fixed-paper, integer-score, set-based multiple-choice, save-before-submit, and auto-submit semantics before decomposition.
- [x] 1.2 Extract exam configuration, timing, publication-readiness, and frozen-pool logic from `exam_service.py` behind the existing service API.
- [x] 1.3 Extract fixed-paper selection, coverage, seed, and score-distribution logic from `exam_service.py` without changing deterministic paper behavior.
- [x] 1.4 Extract attempt start/read/save/submit and retake lifecycle logic from `exam_service.py` while preserving row-lock and transaction boundaries.
- [x] 1.5 Extract result construction, release, incident, and reporting helpers from `exam_service.py`, retaining a compatibility facade for existing routes and tests.
- [x] 1.6 Split `ExamTakingPage.tsx` state into focused countdown, attempt-session, draft/save queue, submission, and view-composition hooks/components without changing current routes or design tokens.
- [x] 1.7 Add an Alembic migration for result-detail release metadata, attempt-session hash/generation, answer revision, void metadata, the operational lock, and administrator audit events.
- [x] 1.8 Update SQLAlchemy models and Pydantic schemas for the migration, including terminal `voided` status and compatibility reads for existing attempts.
- [x] 1.9 Add migration upgrade tests against PostgreSQL and prove existing result visibility, attempt snapshots, and submitted records remain readable.

## 2. Named Operators, Sessions, And Audit

- [x] 2.1 Add formal configuration fields for primary and backup operator credentials, backup-enabled state, separate admin/candidate TTLs, and four-hour internal-profile validation.
- [x] 2.2 Update admin login to authenticate either named operator, carry the operator subject in signed tokens, and reject the disabled backup operator with a uniform failure.
- [x] 2.3 Update admin and candidate token verification to use separate four-hour TTLs while preserving signed `X-Admin-Token` and `X-Candidate-Token` contracts.
- [x] 2.4 Implement the append-only-through-the-application audit service with allowlisted metadata and hashed request-source data.
- [x] 2.5 Emit audit events for login, publish, result release, imports, operator enablement, retake, void, retention deletion, backup/restore, and session closure without logging secrets or uploaded content.
- [x] 2.6 Add local PowerShell commands that atomically enable or disable the backup operator in protected configuration and recreate only the required backend service.
- [x] 2.7 Add a guarded close-exam service check and PowerShell command that refuses in-progress attempts, rotates `TOKEN_SECRET`, recreates the backend, and proves old tokens fail and readiness recovers.
- [x] 2.8 Add backend and deployment tests for named operators, disabled backup access, separate TTL expiry, secret isolation, audit immutability, sensitive-data redaction, and guarded global revocation.

## 3. Windows Release And Split Ingress

- [x] 3.1 Define the protected `C:\ProgramData\InternalExam` configuration, release, backup, evidence, and diagnostic directory contract and validate NTFS ACL expectations in preflight.
- [x] 3.2 Add a versioned PowerShell install/start/stop/status workflow that requires only Docker Desktop and PowerShell on the Windows host.
- [x] 3.3 Add release manifest and checksum generation tied to one Git commit and application version, excluding formal secrets and data.
- [x] 3.4 Pin backend, frontend, PostgreSQL, Nginx, and operations base images by digest and expose the digests in release evidence.
- [x] 3.5 Add commit-tagged image build and disposable Windows staging Compose workflows with separate ports, project name, database volume, and media volume.
- [x] 3.6 Split Nginx/Compose into a private-LAN candidate gateway on `8080` and a loopback operator gateway on `8081`.
- [x] 3.7 Deny admin, operational, readiness-detail, `/docs`, and `/openapi.json` routes on the candidate gateway while preserving candidate API/media behavior.
- [x] 3.8 Add `restart: unless-stopped` and bounded Docker log rotation to every formal service and test the rendered Compose contract.
- [x] 3.9 Add a hard Windows preflight for Docker state, internal configuration, fixed bind, split exposure, service health, migration, time, disk, SMTP, backup, browser smoke, and release checksums.
- [x] 3.10 Add previous-release promotion and guarded paired-backup rollback workflows, with separate tested paths for pre-migration failure and post-migration/formal-write failure.
- [x] 3.11 Add deployment tests proving the worker/frontend receive no operator or signing secrets and the LAN cannot reach loopback-only surfaces.
- [x] 3.12 Require an exact typed data-loss confirmation for same-host restore of the pre-upgrade backup when post-backup writes may be discarded, and record the expected loss in non-secret rollback evidence.

## 4. Publication, Timing, And Write Gates

- [x] 4.1 Add a service-layer publication-readiness result for unique stems, type/category coverage, score/pass rules, 120-minute limit, 15-minute start grace, roster email readiness, and prospective pool count.
- [x] 4.2 Add read-only admin publication-readiness schemas/API and a local admin UI that distinguishes blockers from warnings.
- [x] 4.3 Require exact-title confirmation and rerun authoritative readiness inside the publish transaction before freezing the pool.
- [x] 4.4 Enforce the 120-minute ceiling for new or updated formal exams while preserving readable legacy records.
- [x] 4.5 Expose eligible exams for OTP-authenticated candidates during the 30-minute early-login window but reject start before `available_from`.
- [x] 4.6 Close new attempt creation 15 minutes after `available_from`, grant full duration to starts within grace, and preserve resume until each attempt's `ends_at`.
- [x] 4.7 Implement the database-backed operational write-freeze lock with owner, acquisition, expiry, release, and retryable conflict semantics.
- [x] 4.8 Add a shared service guard that rejects question/candidate/roster imports, exam mutations, and video mutations while a formal attempt is in progress.
- [x] 4.9 Apply the backup write-freeze guard to practice submissions, learning progress, uploads, imports, and admin mutations while leaving reads available.
- [x] 4.10 Add backend/API/frontend tests for publication blockers, title confirmation, timing boundaries, in-exam write protection, backup lock expiry, and unchanged allowed reads.

## 5. Single-Device Attempts And Draft Recovery

- [x] 5.1 Generate an opaque attempt-session credential at start, store only its hash/generation, and require it for attempt read, save, and submit.
- [x] 5.2 Add a fresh-OTP explicit takeover API that rotates the attempt-session generation without changing snapshots, saved answers, or deadline.
- [x] 5.3 Add monotonically increasing answer revisions to save responses and reject stale device revisions without overwriting newer answers.
- [x] 5.4 Preserve row-lock serialization between revisioned save, manual submit, auto-submit, takeover, and void transitions.
- [x] 5.5 Extend the frontend API client and candidate session model to carry the attempt-session credential only in session-scoped browser state.
- [x] 5.6 Persist pending answer selections in `sessionStorage` keyed by candidate, attempt, session generation, and answer revision.
- [x] 5.7 Restore only matching pending drafts, retry when connectivity returns, surface pending/saving/saved/offline/conflict/error states, and clear drafts after submit or invalidation.
- [x] 5.8 Add backend PostgreSQL concurrency tests and frontend tests for stale revisions, multi-tab/device conflicts, takeover, reload recovery, offline submit failure, and draft cleanup.

## 6. Results, Incidents, Retakes, And Reports

- [x] 6.1 Add `result_details_released_at` and releasing-operator behavior for new exams while migrating already visible historical results to preserve their visibility.
- [x] 6.2 Default new candidate results to score/pass only and omit answer/analysis snapshots until release.
- [x] 6.3 Add a loopback-admin one-time result-detail release API/UI that requires all attempts terminal, exact confirmation, and audit, and cannot be reversed or repeated.
- [x] 6.4 Remove or reject candidate-facing ranking and keep ranking/report APIs on the loopback-admin surface.
- [x] 6.5 Implement terminal `voided` attempts with operator, timestamp, and reason while preserving snapshots, answers, and timing evidence.
- [x] 6.6 Exclude voided attempts from auto-submit, normal score/accuracy/wrong/pass/attendance/ranking queries and exports while adding an admin incident view.
- [x] 6.7 Implement previewed, audited bulk retake grants with row-level granted/skipped outcomes and at most one unused grant per eligible candidate.
- [x] 6.8 Add a formal-exam evidence-bundle service that records release, preflight, pool/roster, SMTP, timing, incident/retake, backup, and close-exam artifact references without secrets.
- [x] 6.9 Add regression tests for hidden/released historical results, irreversible release, candidate ranking denial, void terminal behavior, report exclusions, bulk-retake idempotency, and evidence redaction.

## 7. Practice Feedback And Wrong-Question Review

- [x] 7.1 Extend practice-submit response schemas and service output with correctness, normalized correct answer, analysis, and selected-versus-correct option comparison.
- [x] 7.2 Preserve pre-submit practice question privacy and candidate-token/active-candidate checks.
- [x] 7.3 Keep each practice submission immutable and create a new `PracticeAnswer` row for every retry rather than rewriting the first result.
- [x] 7.4 Add candidate-scoped wrong-question queries with category filters and mastered state derived from later correct attempts while retaining prior mistakes.
- [x] 7.5 Update practice UI to lock submitted feedback, show answer/analysis comparison, start a new retry, and navigate/filter the lightweight wrong-question review.
- [x] 7.6 Update API/docs and add backend/frontend tests for feedback visibility, first-result locking, repeated history, mastered state, and cross-candidate isolation.

## 8. Retention, Backup, Restore, And Storage

- [x] 8.1 Implement a 12-month retention preview for exam-scoped personal, attempt, answer, result, and evidence data with referential-safety explanations.
- [x] 8.2 Add versioned Excel/JSON archive and manifest generation for explicit eligible exam IDs without deleting source data.
- [x] 8.3 Add the operator-confirmed deletion service requiring a current preview, archive, verified paired backup, explicit IDs, and audit event.
- [x] 8.4 Move application-specific backup/restore logic into versioned one-shot containers and expose only PowerShell orchestration on Windows.
- [x] 8.5 Implement daily data-change detection and opportunistic paired backup using the write-freeze lock, including skip and expired-lock recovery behavior.
- [x] 8.6 Retain only the latest three verified local backups and synchronize verified post-exam backups to a configured encrypted second location for 12 months.
- [x] 8.7 Record second-copy protection/synchronization status without claiming success when the destination is unavailable or unverified.
- [x] 8.8 Add first-release and quarterly disposable restore-drill workflows that source the second copy and validate migration, counts, media integrity, and cleanup.
- [x] 8.9 Calculate the 20 GiB and three-times-footprint storage reserve and enforce it before video upload and release upgrade without blocking formal answer traffic.
- [x] 8.10 Add tests for retention eligibility, archive-before-delete safeguards, operational-lock backup behavior, local pruning, failed second-copy sync, restore isolation, and disk reserve boundaries.

## 9. Operations UI, Offline Assets, And Client Quality

- [x] 9.1 Add loopback-only operations schemas/APIs for version, migration, service/worker health, lock, disk, backup, second copy, restore drill, retention, and security-scan state.
- [x] 9.2 Build the Academic Editorial operations page with distinct loading, current, degraded, stale, skipped, and failed states.
- [x] 9.3 Add a PowerShell diagnostic export that collects the bounded non-secret operations snapshot, service status, release manifest, and rotated logs with checksums.
- [x] 9.4 Remove Google Fonts and other runtime external requests, bundle required font assets/licenses or use system fallbacks, and tighten CSP to required same-origin sources.
- [x] 9.5 Add a candidate browser/device self-check for supported current Edge/Chrome, Android Chrome, and iOS Safari, with a blocking warning for legacy or embedded browsers.
- [x] 9.6 Add representative accessibility checks for labels, semantics, keyboard/focus, contrast, errors, zoom, responsive layout, and mobile fixed controls.
- [x] 9.7 Add tests proving the built candidate/admin runtime loads and remains usable without public Internet access.

## 10. Automated Release Gates

- [x] 10.1 Add Playwright browser E2E for local operator login/publication, OTP candidate login, start, revisioned save, reload/draft recovery, submit, result release, device conflict, and close-exam invalidation.
- [x] 10.2 Run the E2E suite through the disposable Nginx/backend/PostgreSQL Windows-equivalent Compose topology and fail release on console, request, route-exposure, or state errors.
- [x] 10.3 Add a reproducible 100-client capacity test for start, save, submit, database connections, and worker health with documented acceptance thresholds.
- [x] 10.4 Add weekly Python/npm dependency and final-image vulnerability scans plus a release dependency/image manifest without automatic deployment.
- [x] 10.5 Block new release evidence on confirmed critical or exploitable high-severity findings and document disposition for non-blocking results.
- [x] 10.6 Add CI checks for pinned image digests, PowerShell syntax, release manifest/checksums, Compose exposure, no third-party runtime requests, and OpenSpec consistency.

## 11. Windows Operations And Formal UAT Documentation

- [x] 11.1 Add a Windows Docker Desktop installation and dedicated operator-account guide covering WSL2, protected directories, NTFS ACLs, fixed IP, firewall, power, time, and update settings.
- [x] 11.2 Document the shared-office-LAN HTTP exception, exact exposed data, compensating controls, and event-triggered reassessment conditions without describing the mode as transport-secure.
- [x] 11.3 Document versioned install, staging, promotion, preflight, close-exam, diagnostics, paired backup, encrypted second-copy, restore drill, and backup-based rollback PowerShell commands.
- [x] 11.4 Update candidate/operator guides for 30-minute login, 15-minute start grace, two-hour maximum, supported browsers, single-device takeover, offline drafts, result release, ranking privacy, void, and bulk retake.
- [x] 11.5 Update practice documentation for immediate feedback, locked submissions, repeat history, and wrong-question mastery over the shared bank.
- [x] 11.6 Update retention, backup, disk-reserve, 24×7 best-effort, formal operator coverage, seven-day release freeze, quarterly maintenance, and quarterly restore-drill policies.
- [x] 11.7 Expand the official UAT and handoff evidence to cover both Windows gateways, real mobile/desktop clients, SMTP fail-closed behavior, in-exam write gates, incidents, second-copy restore, and session closure.

## 12. Future Mac-To-Windows Cutover Verification And Promotion Readiness

> Tasks 12.4 and 12.5 are retained for a future Mac-to-Windows cutover. They require native Linux AMD64 Windows evidence and cannot be completed with macOS staging, promotion, or UAT evidence alone. The selected Mac formal source project must be stopped as a whole before Windows can accept writes; selecting Mac does not mean either host has passed its host-specific acceptance gate.

- [x] 12.1 Run backend format, lint, type checks, SQLite-compatible tests, and the complete disposable PostgreSQL suite with zero conditional concurrency skips.
- [x] 12.2 Run frontend format, unit/component tests, lint, build, accessibility checks, and the core browser E2E suite.
- [x] 12.3 Run `openspec validate --all --strict`, Compose render/exposure tests, PowerShell checks, security scans, offline-asset checks, and the 100-client capacity gate.
- [ ] 12.4 From the selected Mac source writer after its own acceptance gate, build native Linux AMD64 images from the same checksummed release inputs and start the disposable Windows staging project; restore the final Mac paired backup, verify migration/head/count/media/SMTP, approved-CIDR and port-negative gates, candidate/admin route separation, service recovery, second-copy restore, diagnostics, and a checksummed cutover manifest containing `datasetId`, source/target `hostId`, previous/next `writerGeneration`, paired-backup checksums, and whole-Mac-project stop proof.
- [ ] 12.5 After 12.4, run Windows `accept-cutover` against the unconsumed manifest, expose no candidate writes until all native AMD64 staging/security/capacity/recovery gates pass, promote only the tested images, run official Windows desktop/phone UAT and real SMTP, close sessions, retain the evidence bundle, and prove Windows is the sole writer. If rollback is required after target writes, first create/verify the latest Windows paired backup and stop the entire Windows formal project before restoring it to Mac or another approved host.
- [x] 12.6 Perform an adversarial final review for HTTP exception accuracy, secret and PII leakage, attempt/session races, snapshot preservation, destructive lifecycle safeguards, rollback feasibility, scope boundaries, and documentation consistency.
