## Context

> **Target update (2026-08-07):** the completed Windows adapter remains supported, but Windows is now a future migration target. Current macOS formal-host requirements and evidence are defined by `support-macos-formal-host-portability`; native AMD64 Windows staging, cutover, and UAT remain mandatory before any future Windows cutover.

The platform already has a complete single-host exam, practice, reporting, OTP, video-learning, worker-health, and paired-backup loop. The selected current formal source/target is macOS, but real Mac host acceptance remains a separate pending gate; this change MUST NOT claim that Mac is ready from planning evidence alone. This change preserves a future Windows computer running Docker Desktop with the WSL2 backend; development and the selected Mac formal writer remain separate until a native AMD64 cutover is deliberately accepted.

The formal instance serves at most 50 concurrent candidates, with a 100-client release load test. Formal exams last at most two hours, use a 30-minute early-login window and 15-minute start grace period, and have a primary operator on duty with a reachable backup operator. Outside exam windows, learning and practice are best-effort 24×7 services with next-business-day recovery.

The office cannot provide a domain, certificate trust distribution, separate VLAN, or dedicated Wi-Fi. Candidate traffic therefore remains HTTP on a shared office LAN. The user explicitly accepts that names, email addresses, OTPs, bearer tokens, answers, and result requests are not transport-encrypted. This design treats that as a first-phase exception with compensating controls, never as HTTPS-equivalent security. It has no calendar expiry, but scope, network, identity, data-sensitivity, or incident changes trigger reassessment.

The change crosses deployment, persistence, authentication, exam delivery, practice behavior, data lifecycle, frontend state, CI, and operations. It must preserve attempt snapshots, fixed-paper selection, set-based multiple-choice scoring, thin routes, Pydantic contracts, and the existing Academic Editorial design system.

## Goals / Non-Goals

**Goals:**

- Make the dedicated Windows host reproducible and operable with only Docker Desktop and PowerShell on the host.
- Enforce separate candidate-LAN and administrator-loopback surfaces and compensate for the accepted HTTP exception with short sessions, local administration, revocation, and reduced exposure.
- Turn publication, exam-day operation, incident recovery, result release, backup, retention, and rollback into explicit, testable state transitions.
- Keep pending answers recoverable through transient mobile/desktop network loss without claiming full offline exam support.
- Make practice a learning workflow that reveals feedback after a locked submission and supports simple wrong-question review.
- Make backup, storage, logs, release evidence, dependency scanning, browser compatibility, and accessibility sustainable for a 24×7 single-host service.
- Reduce change risk by splitting the largest exam backend and frontend modules without changing their public contracts except where this change explicitly specifies new behavior.

**Non-Goals:**

- TLS, domain or CA management, network segmentation, or a claim that HTTP is secure on a shared office LAN.
- Redis, Celery, a durable email queue, microservices, multi-host HA, automatic failover, or a zero-downtime hardware-failure guarantee.
- Full offline exams, global timer suspension, manual OTP bypass, administrator score editing, or automatic continuation after a serious host outage.
- Complex RBAC, multi-tenancy, SSO, external observability platforms, 24×7 operator response, or full proctoring/anti-cheat controls.
- A separate practice question bank, Word import, course management, or other LMS expansion.

## Decisions

### 1. Treat Windows Docker Desktop as a future tested release target

The formal runtime remains Docker Compose, but future Windows becomes an explicit release target rather than an assumed side effect of Linux-compatible containers. A release bundle contains the source/build inputs, Compose files, PowerShell entrypoints, self-hosted assets and licenses, a Git commit/version manifest, and checksums. Formal `.env` files, backups, evidence, and diagnostics live outside the version directory under a documented `C:\ProgramData\InternalExam` layout protected by NTFS ACLs.

The Windows host does not require Git, Python, `uv`, Node.js, or Bash. PowerShell orchestrates versioned one-shot operations, while application-specific validation and backup logic runs in pinned containers. Base images are locked by digest. A release is built once for a commit, tagged with that commit, exercised in a disposable same-host Compose project with distinct ports and volumes, and then promoted to the formal project without rebuilding from a floating tag.

Direct `git pull main` and native Windows installations were rejected because they make rollback and host parity difficult. A private image registry was not required because the small deployment can transfer a checksummed source/release bundle and build during a maintenance action before UAT.

### 2. Use explicit same-host and cross-host rollback contracts

The host retains the previous accepted release bundle and images. For a same-host version rollback, the operator selects the previous release and the verified paired pre-upgrade backup; if restoring it can discard writes made after the backup, an explicit typed data-loss confirmation is required and recorded before the destructive restore. `alembic downgrade` is not the normal path because it cannot guarantee data and media consistency.

Cross-host rollback is a different operation. A target that accepted writes must first create and verify its latest paired backup, then stop the entire target formal Compose project before restoring that newest backup to the source or another approved host. The stale source cannot simply restart. If the target accepted no writes, stop the entire target project and reopen the unchanged source only after writer-manifest reconciliation and preflight.

CI remains the first gate for this change. For the future Windows promotion, the native AMD64 disposable Windows project is the host-specific gate before formal target acceptance, followed by Windows cutover, UAT, and evidence; it does not establish current Mac readiness. Release evidence includes the commit, image digests, security-scan result, Windows preflight, database migration head, browser E2E result, 100-client capacity result, real SMTP check, paired backup and restore result, and post-promotion health.

### 3. Fence one formal writer across hosts

The shared portability contract assigns every formal dataset an immutable `datasetId`, every host/project a `hostId`, and every accepted writer a monotonic `writerGeneration`. `prepare-cutover` on the source creates a checksummed manifest with these identities, release/image identity, final paired-backup checksums, and whole-project stop proof; it must stop all source services, not only the candidate gateway. `accept-cutover` on the target validates the unconsumed manifest, isolated restore, target preflight, and absence of source services before exposing candidate writes and recording the next generation. This change consumes that contract for future Windows acceptance; it does not redefine the Mac-owned source protocol.

### 4. Split the candidate and operator ingress contracts

Compose exposes two Nginx entrypoints:

- Candidate LAN: `http://<fixed-private-ip>:8080`, serving candidate login, candidate exam/practice/learning APIs, candidate SPA routes, and published media.
- Operator loopback: `http://127.0.0.1:8081`, serving administrator pages/APIs, operational status, diagnostics, readiness details, `/docs`, and `/openapi.json`.

The LAN gateway rejects `/admin`, `/api/admin/*`, operational endpoints, readiness detail, and OpenAPI routes before proxying. Backend, PostgreSQL, the direct frontend, and worker remain unexposed to the LAN. Relying only on operator policy or container-observed source IP was rejected because Docker Desktop port forwarding can obscure client addresses and policy cannot prevent accidental remote administration.

### 5. Compensate for the accepted HTTP exception without hiding it

Admin and candidate token lifetimes become independently configurable and are fixed at four hours for the formal profile. New or updated formal exams are capped at 120 minutes, leaving time for early login and short recovery. Candidate and admin tokens remain in `sessionStorage`, not persistent browser storage.

A close-exam PowerShell operation first proves that no attempt is `in_progress`, rotates `TOKEN_SECRET` with a cryptographically random value, recreates the backend, and verifies readiness. This invalidates every prior admin and candidate token, including learning/practice sessions. The operation is guarded against accidental execution during an exam and emits non-secret evidence.

The HTTP exception is documented with the exact exposed data and compensating controls. It must be reassessed if concurrency exceeds 50, the network boundary changes, remote administration is requested, data sensitivity expands, a suspected interception incident occurs, or trusted DNS/TLS/network-isolation options become available.

### 6. Use two configured operators with one permission set

The formal backend accepts a primary and backup operator credential pair. Both map to the same administrator permission set; this is not RBAC, and only one operator mode is active at a time. Backup disabled means primary-only; enabling backup atomically switches to backup-only and immediately invalidates primary credentials and existing primary tokens; disabling backup switches back to primary-only and invalidates backup credentials and existing backup tokens. The backup credential is disabled by default and can be enabled or disabled only through the local PowerShell workflow. Tokens carry the named operator subject so audit events identify who acted; the two operators are never valid concurrently.

An append-only-through-the-application `admin_audit_event` table stores operator subject, action, target type/id, result, allowlisted non-sensitive metadata, a request-source hash, and timestamp. No API updates or deletes audit rows. Login, publish, result release, imports, retake/void actions, retention deletion, backup/restore, operator enablement, and session closure produce audit events. Secrets, OTPs, bearer tokens, full files, and unrestricted request bodies are never stored.

### 7. Make publication an atomic readiness decision

A read-only publication-preflight service evaluates the deduplicated active question pool, type and category coverage, fixed-paper rule, total/pass score, 120-minute limit, roster/email readiness, start window, and frozen-pool result. It returns blockers, warnings, and a non-secret readiness fingerprint.

Publishing requires the operator to enter the exact exam title. The publish transaction reruns the authoritative checks and freezes the pool; it does not trust an earlier frontend result. This avoids a time-of-check/time-of-use gap while keeping the existing snapshot and frozen-pool rules.

Candidate OTP login opens 30 minutes before `available_from`. A formal start window closes 15 minutes after `available_from`; candidates starting within that grace period receive the full configured duration. Existing in-progress attempts may resume after the start cutoff until their own `ends_at`. Answers and analysis cannot be released until every attempt is terminal.

### 8. Enforce exam-time and backup-time mutation gates in services

Admin mutation services for question/candidate imports, roster changes, video upload/status edits, exam edits/publication, and other non-essential writes check a shared operational guard. When any formal attempt is in progress, those mutations fail with a stable conflict response while health, operational views, reports, candidate answer saves, and submit remain available.

A small database-backed operational lock coordinates opportunistic backup. Backup starts only when no formal attempt is in progress, obtains the lock, waits for in-flight protected writes, and briefly blocks new practice submissions, learning-progress changes, uploads, and admin mutations. Reads remain available. The lock has an owner and expiry so a crashed backup cannot leave the service permanently read-only.

### 9. Add single-device ownership and revisioned answer recovery

Starting an attempt returns an opaque attempt-session credential. Only a hash and generation are stored on the attempt; subsequent attempt read/save/submit calls require the credential. A newly OTP-authenticated candidate can explicitly take over the attempt, rotating the generation and causing the prior device to receive a conflict response. Two tabs or devices cannot silently use last-write-wins saves.

Answer saves carry an attempt answer revision and return the next revision. The exam page writes pending selections synchronously to `sessionStorage` under candidate, attempt, and attempt-session keys. On reload it restores only a matching draft and merges it against the server revision. Network restoration triggers bounded upload retry; a stale revision requires reconciliation rather than overwriting newer server state. Successful submission clears the draft.

This is not an offline exam: the countdown uses server-derived time, the candidate cannot start or submit without the backend, and local data does not change scoring until the server accepts it.

### 10. Separate score availability from one-time detail release

New exams default to candidate-visible score and pass status only. Correct-answer and analysis snapshots remain persisted but are returned only after an administrator executes a one-time detail release and no attempt remains in progress. The exam records `result_details_released_at` and the releasing operator. Release is irreversible through the application.

Historical exams retain their current answer-visibility behavior through migration data so already visible results do not unexpectedly disappear. Candidate ranking is removed from candidate-facing behavior; ranking and full result reports remain available only on the local admin surface.

### 11. Model incident invalidation rather than editing scores or pausing clocks

`ExamAttempt.status` gains `voided` with timestamp, operator, and reason. Voiding preserves attempt snapshots, answers, timing, and evidence but excludes the result from rankings, pass rates, attendance completion, and standard score aggregates. The auto-submit worker ignores terminal voided attempts.

An audited bulk-retake operation previews affected candidates, skips ineligible or already-granted rows, atomically voids selected attempts when requested, and creates at most one unused grant per eligible candidate. A host/network incident longer than the accepted short interruption is handled by stopping/rescheduling and using this flow; no global timer pause or administrator score adjustment is introduced.

### 12. Make practice immediate-feedback learning over the shared bank

Practice question listing remains token-gated and continues omitting answers before submission. The submit response now returns `is_correct`, the normalized correct answer, analysis, and selected/correct option comparison. Each submission inserts an immutable `PracticeAnswer`; viewing feedback locks that record, while later attempts create new rows.

Wrong-question review groups the candidate's incorrect practice history by question and supports category filters and resubmission. A later correct submission marks the item mastered for the current view without deleting earlier mistakes. No `practice_enabled` flag or separate bank is added because the user explicitly accepts that the formal bank is learnable and exposed through practice.

### 13. Add bounded lifecycle and consistent online backup

Exam-scoped online history becomes eligible for archival deletion 12 months after its final activity. A preview operation lists affected exams and related personal/result records. The operator exports a versioned Excel/JSON archive plus manifest, creates a paired backup, and then confirms deletion by explicit exam IDs. Question-bank and video-library assets remain governed by their own archive actions; active or still-referenced candidate identities are not deleted accidentally.

The daily backup task is opportunistic rather than a fixed maintenance window: it runs only when data changed, no formal attempt exists, and the write-freeze lock is available. Local storage retains the latest three verified backups. A configured encrypted second location retains each post-exam final backup for 12 months. Failed, partial, or unverified backups never enter the retention set. The first formal release and each quarter restore from the second copy into disposable resources.

Video upload and release preflight enforce a reserve of at least 20 GiB and at least three times the current database-plus-media footprint. Falling below the reserve blocks uploads and upgrades, not ongoing formal answer traffic.

### 14. Keep observability local and bounded

Every Compose service uses size/file-count log rotation and `restart: unless-stopped`. Docker Desktop starts after the dedicated Windows operator signs in; automatic container recovery never replaces the manual formal-exam preflight. The Windows host uses AC power, sleep/hibernate suppression, time synchronization, and exam-window update/restart suppression without permanently disabling security updates.

The loopback operations page shows version, migration head, service health, worker heartbeat, last backup/second-copy/restore-drill status, disk reserve, operational lock, pending retention actions, and security-scan status. A PowerShell diagnostic command exports those signals plus redacted configuration facts and bounded logs. Formal-exam evidence is checksummed and excludes secrets, tokens, OTPs, and full sensitive configuration.

No Prometheus, Grafana, paging service, or HA control plane is added. Outside formal exams, incidents may wait until the next business day.

### 15. Remove runtime third-party dependencies and define client quality gates

Google Fonts and all other runtime third-party requests are removed. Required fonts and licenses are bundled or replaced with the documented system-font stack, and CSP permits only same-origin runtime assets. Supported clients are current stable Edge/Chrome on Windows, current Chrome on Android, and the current major Safari on iOS; in-app and legacy browsers receive an explicit unsupported warning.

Release gates add representative accessibility checks for semantics, focus, keyboard use, contrast, errors, zoom, and responsive layout. Browser E2E covers local admin login/publication, OTP login, start/save/reload/submit, offline-draft recovery, detail release, single-device conflicts, and close-exam revocation through the real Nginx/PostgreSQL stack.

### 16. Refactor only behind preserved contracts

`exam_service.py` is decomposed into configuration/publication, paper generation, attempt lifecycle, result/incident, and shared query modules under `backend/app/services/`. `ExamTakingPage.tsx` delegates countdown, attempt-session ownership, revisioned local draft/save queue, and view composition to focused hooks/components. Routes remain thin, API access remains in `frontend/src/api/`, and the existing snapshot/fixed-paper/scoring contracts remain regression-tested.

This behavior-preserving decomposition is staged before or alongside the affected features; a broad rewrite or new state-management framework was rejected.

## Risks / Trade-offs

- **[HTTP on a shared office LAN exposes identity, OTP, token, answer, and result traffic]** → Keep the exception explicit, isolate administrator traffic to loopback, shorten and revoke sessions, minimize LAN routes, and force reassessment on defined boundary changes or incidents.
- **[Windows Docker Desktop depends on an interactive Windows login]** → Use a dedicated operator account, automatic Docker Desktop startup, restart policies, and a required post-reboot preflight; do not claim server-grade unattended HA.
- **[Rotating `TOKEN_SECRET` logs out practice and learning users]** → Run closure only after formal attempts end, communicate the event, and make re-login the intended recovery.
- **[Attempt-session credentials add another client state]** → Store only a hash server-side, scope it to one attempt, rotate on takeover, keep it in session storage, and test multi-tab/device conflicts.
- **[Local drafts can be stale]** → Pair drafts with attempt-session generation and server revision; never overwrite a newer server revision automatically.
- **[Write freezes briefly reject 24×7 learning/practice writes]** → Keep freezes opportunistic and short, expose retryable status, skip when formal attempts exist, and expire abandoned locks.
- **[Two named configured operators add secret configuration]** → Keep one permission set, default-disable backup access, protect the external `.env` with NTFS ACLs, and never expose secrets to worker or evidence output.
- **[Irreversible result-detail release can leak a reusable bank]** → Require all attempts terminal, typed confirmation, and audit; the user explicitly accepts shared-bank exposure through practice.
- **[Voided attempts complicate reporting]** → Treat `voided` as terminal everywhere, exclude it from normal aggregates, retain it in incident views, and add cross-report regression tests.
- **[Retention deletion is destructive]** → Require preview, export, verified backup, explicit IDs, audit, and referential-integrity checks; never silently auto-delete.
- **[Pinned digests age]** → Scan weekly and update intentionally in tested maintenance releases rather than floating at build time.
- **[The umbrella change is large]** → Implement in independently verifiable phases with migrations and public-contract tests before Windows promotion.

## Migration Plan

1. Add migrations and compatibility reads for named operators/audit events, result-detail release state, attempt-session generation and answer revision, void metadata, and the operational lock. Preserve existing attempt snapshots and already visible historical result details.
2. Decompose the core backend/frontend modules behind the existing test suite before changing their external behavior.
3. Add separate token TTLs, operator subjects, backup-account gating, audit emission, close-exam secret rotation support, and split LAN/loopback ingress. Verify that candidate LAN routes cannot reach admin or OpenAPI surfaces.
4. Add publication preflight, duration/start-window validation, exam-time write guards, attempt-session ownership, revisioned saves, local drafts, one-time detail release, void/bulk retake, and report exclusions.
5. Change practice submit schemas and UI to reveal feedback and add wrong-question review. Update API documentation and tests that previously asserted blind responses.
6. Add lifecycle preview/export/delete services, operational locking, opportunistic backup, second-copy retention status, disk reserve checks, operations UI, logging limits, diagnostics, and evidence manifests.
7. Add PowerShell release/preflight/backup/restore/close/diagnostic workflows, self-hosted assets, pinned image digests, scheduled security scans, browser E2E, accessibility checks, and the 100-client capacity test.
8. For the future Mac-to-Windows move, build native Linux AMD64 images from the same checksummed release inputs, restore the final Mac paired backup into a disposable Windows project, run Windows staging and target gates, execute the shared `prepare-cutover`/`accept-cutover` flow with the entire Mac formal project stopped, then run real SMTP and browser UAT and retain the evidence bundle.

Same-host version rollback uses the previous release bundle and the verified pre-upgrade paired backup; restoring it requires an exact data-loss confirmation whenever post-backup writes may be discarded. Cross-host rollback after target writes first creates and verifies the latest target paired backup, stops the entire target formal project, and restores that newest backup to the source or another approved host. If the target accepted no writes, stop it as a whole and reopen the unchanged source only after writer-manifest reconciliation and preflight. Neither path uses a generic downgrade, stale source data, or an unguarded destructive restore command.

## Open Questions

None. The operating platform, 24×7 service boundary, shared-office-LAN HTTP exception, capacity, operator model, recovery posture, retention, practice feedback, browser support, and excluded architecture have been explicitly confirmed.
