## 1. Contract Baseline And Migration Preflight

- [x] 1.1 Add a read-only account-migration preflight service and operator command that reports missing, malformed, non-normalized, and case-insensitive duplicate real-account emails without changing data or exposing full email addresses.
- [x] 1.2 Extend the preflight to detect sentinel contamination, historical attempts without an exam scope, and scope rows that cannot receive required roster snapshots; make every finding block migration rather than infer or merge identity.
- [x] 1.3 Add focused preflight tests for clean data and each blocker class, including proof that no account, scope, attempt, or login-challenge row is mutated on failure.
- [x] 1.4 Gate the destructive upgrade on the selected formal writer's exact `datasetId`/`hostId`/`writerGeneration` whole-project fence, a verified paired PostgreSQL/media backup plus independently stored encrypted second copy, the coordinated write-freeze lock, and confirmation that no formal attempt is in progress.
- [x] 1.5 Document and test the maintenance failure path so a failed gate leaves the current schema and writers unchanged and emits only redacted operator evidence.
- [x] 1.6 Capture a repository-wide legacy-contract inventory before migration, classifying runtime/API/UI/import/export/report/learning references for removal and immutable historical Alembic or explicit migration fixtures that remain audit-only.

## 2. Account, Challenge, And Scope Persistence

- [x] 2.1 Add account lifecycle and normalized-email model/schema support while retaining the existing `candidate` primary key, `candidate_id` foreign keys, and `candidate:<id>` token subject for compatibility.
- [x] 2.2 Add an additive Alembic migration for `pending`/`active`/`inactive` status, nullable pre-completion display name, normalized email constraints, email-bound login challenges, hashed registration-completion metadata, and bounded cleanup indexes.
- [x] 2.3 Extend `exam_candidate_scope` with required normalized `roster_email`/`roster_name`, optional department/position/exam-group/`roster_remark`, `not_sent|sent|failed` invitation state, last-attempt/sent timestamps, sanitized error class, claim timestamp/owner, and indexes plus database/transaction uniqueness for both `(exam_id, candidate_id)` and `(exam_id, roster_email)`.
- [x] 2.4 In the additive migration, expire legacy open challenges, normalize valid real-account emails, and backfill all existing scope snapshots before source fields are removed; require operators to resolve every preflight-reported historical attempt without a scope before the migration can run, and never synthesize that formal identity inside the destructive transaction.
- [x] 2.5 Add migration assertions for account/scope/attempt counts, normalized-email uniqueness, snapshot completeness, and historical foreign-key preservation, and stop before destructive changes when any assertion fails.
- [x] 2.6 Add the destructive migration step that removes the login sentinel and drops `employee_no`, `phone_suffix`, global `should_attend`, global organization/personnel fields, and their obsolete indexes/constraints only after the verified backfill.
- [x] 2.7 Make the destructive migration downgrade explicitly non-lossless and direct operators to paired-backup restore rather than fabricating deleted personnel or attendance data.
- [x] 2.8 Add disposable-PostgreSQL migration tests covering upgrade from the current head, every preflight blocker, normalized-email race protection, successful backfill, legacy-column absence, and preserved historical results.

## 3. Email OTP Registration And Account APIs

- [x] 3.1 Replace candidate login request schemas with a strict email-only contract that rejects legacy identity keys and add discriminated OTP verification responses for `authenticated`, `registration_required`, and verified-but-`account_unavailable` outcomes.
- [x] 3.2 Centralize trim-plus-lowercase email normalization and syntax validation for authentication, registration, profile, import, scope, and administrator account lookups without provider-specific alias rewriting.
- [x] 3.3 Rewrite OTP challenge creation to persist and commit an email-bound challenge before bounded SMTP delivery, invalidate older open challenges for that email, and return the uniform challenge envelope without using a sentinel row.
- [x] 3.4 Enforce the six-digit, ten-minute, single-use, five-attempt, and sixty-second resend contracts atomically for active, pending, inactive, and previously unknown email paths; an inactive mailbox receives and may verify the OTP but receives only `account_unavailable` until administrator reactivation.
- [x] 3.5 Enforce configured persisted per-email, request-source, and global OTP send windows across process restarts and workers while retaining the bounded in-memory burst guard; keep invitation batch counters separate and ensure the first-phase OTP expiry and returned copy resolve consistently to ten minutes.
- [x] 3.6 Implement OTP verification so active accounts receive a candidate token of at most four hours, while new or pending accounts receive only a hashed, short-lived, one-time registration-completion credential.
- [x] 3.7 Implement transactional registration completion that requires a non-empty display name, consumes the completion credential once, creates or activates the normalized-email account, handles uniqueness races, and never overwrites an existing active display name.
- [x] 3.8 Add authenticated account-profile read/update APIs that expose normalized email as read-only, permit display-name changes only, and reject email replacement, password fields, and physical deletion.
- [x] 3.9 Add bounded loopback-admin account search by normalized email/display name/status and completed-account active↔inactive controls through the existing admin authentication boundary; keep pending→active exclusive to registration completion, reject incomplete activation, and preserve all scopes and histories.
- [x] 3.10 Extend audit and operational logging allowlists for account and auth events using IDs, counts, status, operator, and hashed source only; exclude plaintext email, OTP, completion credential, candidate token, SMTP secret, and user-specific URLs.
- [x] 3.11 Add batch-bounded opportunistic cleanup for expired challenges and registration-completion credentials without a new queue or worker, and test that it preserves unexpired and retention-required audit evidence.
- [x] 3.12 Add backend tests for existing-account login, open registration, pending imported accounts, inactive accounts, completion expiry/replay, resend invalidation, attempt exhaustion, uniqueness races, immutable email, profile edits, admin lifecycle controls, SMTP transport modes, and uniform/redacted failures.

## 4. Active-Account And Formal-Scope Authorization

- [x] 4.1 Change the shared candidate dependency to load the current account and require `active` status on every authenticated request rather than trusting token issuance-time status alone.
- [x] 4.2 Apply the shared status gate to learning, practice, wrong-question review, exam discovery/start, attempt read/save/submit/result/takeover, and profile routes, retaining service-level ownership checks as defense in depth.
- [x] 4.3 Treat audited completed-account deactivation/reactivation as a safety/recovery exception allowed during an in-progress attempt, make deactivation reject the next candidate request without deleting or mutating the attempt, and preserve server-side overdue auto-submit while other non-essential admin mutations remain gated.
- [x] 4.4 Remove global `should_attend`, employee-number, phone-suffix, and mutable profile-field eligibility checks from formal services and require the matching exam scope for discovery, start, resume, attempt access, result access, and retake operations.
- [x] 4.5 Preserve four-hour token expiry and the existing guarded close-exam invalidation boundary, and make candidate 401 handling distinguish authentication failure from normal timing, attempt, result-release, and scope restrictions.
- [x] 4.6 Add authorization matrix tests for active, pending, inactive, scoped, and unscoped accounts across every candidate endpoint, including a mid-attempt deactivation and later operator reactivation path.

## 5. Email-Keyed Roster Import And Publication Freeze

- [x] 5.1 Replace the exam-roster workbook/template/API contract with required `email` and `candidate_name` plus optional department, position, exam group, and remark fields, preserving the configured file-size, row-count, and worksheet-count bounds.
- [x] 5.2 Retire the standalone global candidate import/template and remove employee-number, phone-suffix, global-attendance, imported-status, and name-only matching from import schemas, templates, results, failure reports, services, routes, tests, and visible documentation.
- [x] 5.3 Rewrite roster import matching to use normalized email only, reuse an existing active or pending account, or create a non-token-capable pending account before adding one draft exam scope.
- [x] 5.4 Persist `candidate_name` as scope-owned `roster_name`, keep optional organization fields on the scope only, never overwrite an active account display name/status, and preserve the account when a draft scope is removed.
- [x] 5.5 Report missing, malformed, duplicate, ambiguous, inactive-account, or legacy-only roster identities as row-level failures without partial access grants or automatic identity merges; require explicit account reactivation before retrying an inactive email.
- [x] 5.6 Add authenticated draft roster list/add/update/remove APIs and reject every roster mutation after publication with a stable conflict response.
- [x] 5.7 Extend publication readiness to validate every scope snapshot and account association, then freeze the complete roster atomically in the same publication boundary that freezes the question pool.
- [x] 5.8 Preserve the existing import/backup write gate so question and exam-roster imports create no batch or rows while an attempt is in progress or the coordinated backup freeze is active.
- [x] 5.9 Add import and publication tests for case-insensitive reuse, pending creation, duplicate rows, optional blanks, reduced template headers, deprecated columns, bounds-before-write, draft deletion, publication freeze, and failure-report export.

## 6. Invitation Delivery And Audit

- [x] 6.1 Add validated configuration for the candidate public base URL, invitation batch cap, delivery-claim expiry, and invitation-specific admin action limits without changing the controlled-LAN or split-ingress boundary.
- [x] 6.2 Add an invitation email template and sender addressed to the frozen scope `roster_email` that uses the existing bounded SMTP adapter, a deterministic diagnostic message identifier, and a configured private-LAN same-origin exam URL containing no OTP, token, invite code, scope identifier, email, or authorization grant.
- [x] 6.3 Implement an explicit post-publication initial-send service that atomically claims eligible `not_sent` scope rows before scheduling bounded in-process delivery and rejects draft/mutable-roster state, an in-progress formal attempt, or the coordinated backup write freeze without changing delivery state.
- [x] 6.4 Persist each recipient outcome independently as `sent` or `failed` with sanitized timestamps/error class, release completed claims, and leave interruption-recoverable stale claims without claiming exactly-once delivery.
- [x] 6.5 Implement a separate failed-only resend service that never resends or downgrades `sent` rows and can recover an expired claim only through a new explicit administrator action.
- [x] 6.6 Add loopback-admin send/resend endpoints whose mutation response reports only accepted/rejected scheduling counts, plus roster-status polling for final per-recipient outcomes and audits that record operator, exam, selected/sent/failed counts, and sanitized outcome classes only.
- [x] 6.7 Add concurrency and failure tests for duplicate admin requests, stale claims, per-recipient isolation, transient/permanent SMTP failures, process interruption, SMTP-success/status-commit ambiguity, batch caps, and redacted evidence.
- [x] 6.8 Extend fake-SMTP capture and focused integration tests to prove publication sends nothing automatically, initial send targets only `not_sent`, resend targets only `failed`, and invitation links are bearer-free.

## 7. Exam Visibility, Shared Practice, And Learning

- [x] 7.1 Remove the obsolete 30-minute roster-login window so platform OTP login is available at any time, and change discovery so every active scoped account sees a published exam immediately with server-calculated availability and `available_from`, regardless of invitation delivery state.
- [x] 7.2 Preserve the backend start prohibition before `available_from`, the configured start grace, full-duration deadline, attempt-session ownership, resume/takeover, snapshots, draft recovery, submit, result-release, incident, void, and retake behavior.
- [x] 7.3 Keep practice and formal exams on the same active question bank, with publication freezing the selected formal pool and no new visibility partition or secrecy claim.
- [x] 7.4 Preserve immutable per-account practice submissions, pre-submit answer privacy, post-submit correctness/correct-answer/analysis/option comparison, category filters, and mastered wrong-question state for every active account.
- [x] 7.5 Update learning and practice schemas/services to use account display name/email/status where identity is required and remove all legacy employee, phone, global-attendance, and global-organization fields.
- [x] 7.6 Add regression tests proving shared-bank selection and fixed-paper invariants, immediate upcoming-exam visibility, pre-open start rejection, unchanged grace/deadline/result/retake rules, per-account practice history isolation, and active-account learning access.

## 8. Frozen-Identity Reporting

- [x] 8.1 Rewrite formal score, attendance, accuracy, wrong-question, ranking, incident, retake, and export queries to read roster identity and organization fields from the relevant frozen exam scope rather than the mutable account row.
- [x] 8.2 Preserve global and `exam_id` report filters, latest-attempt attendance classification, void exclusions, score/accuracy/wrong-question aggregation, administrator-only ranking, and submitted/auto-submitted semantics.
- [x] 8.3 Ensure pending or inactive scoped recipients and scoped recipients with no attempt remain represented by frozen roster identity in applicable attendance/history reports, while deactivation never deletes historical results.
- [x] 8.4 Remove `employee_no`, `phone_suffix`, and `should_attend` from report schemas, filters, tables, workbook sheets, headers, cells, and learning-report contracts; use account identity only for non-formal learning reports.
- [x] 8.5 Preserve the canonical workbook sheet/status labels and formula-character escaping while adding frozen roster email/name and optional scope organization columns.
- [x] 8.6 Add report tests showing profile edits and account deactivation do not alter formal rows, each global row keeps its own exam snapshot, absent/history rows include the full frozen scope as specified, voided attempts remain excluded, and removed fields never appear in JSON or Excel.

## 9. Candidate Frontend Authentication And Profile

- [x] 9.1 Update frontend auth/account types and API modules for email-only challenges, discriminated verification, registration completion, profile read/update, account status, and read-only email without hand-written page fetches.
- [x] 9.2 Replace the current name/employee-number login form with the email request and OTP verification steps, including masked-email guidance, ten-minute validity text, resend countdown, neutral invalid-code errors, an actionable verified `account_unavailable` notice, and the exact confirmed Chinese copy.
- [x] 9.3 Add the separate registration-completion route/form with required display name, short-lived credential handling, accessible validation, and no candidate session before successful completion; a pending invite's roster name may be suggested but must be explicitly confirmed or edited and never rewrites the scope snapshot.
- [x] 9.4 Add an authenticated profile page that edits display name only, renders normalized email as read-only, and exposes no email-change, password, remember-me, or account-delete controls.
- [x] 9.5 Preserve validated same-origin `returnTo` state across unauthenticated route guards, OTP request/verification, registration completion, session restoration, and invitation deep links; reject external, protocol-relative, and malformed targets.
- [x] 9.6 Keep candidate credentials in session-scoped storage only and clear account, attempt-session, and draft state on logout, token expiry, guarded revocation, or inactive-account 401 while preserving a safe current destination for re-authentication.
- [x] 9.7 Update candidate layout, top navigation, name plate, learning/practice/wrong-question surfaces, and formal-exam contexts to use `用户` versus `应考人员` consistently and remove every employee-number/phone/global-attendance display.
- [x] 9.8 Add focused frontend tests for existing login, open registration, pending completion, replay/expiry errors, exact copy, profile editing, immutable email, return-target safety, invitation return through registration, four-hour/sessionStorage behavior, 401 cleanup, keyboard/focus semantics, and narrow-viewport usability.

## 10. Candidate Exam And Admin Frontend

- [x] 10.1 Update candidate exam types/list/start pages to show published scoped exams immediately, distinguish invited/upcoming/startable/unavailable/loading/empty/error states, display opening time, and keep start disabled before backend eligibility.
- [x] 10.2 Add an admin account directory with search and completed-account activate/deactivate actions, clear pending/active/inactive states, and no email-edit or delete control.
- [x] 10.3 Replace admin roster import/table/edit UI with the reduced email/name/optional-organization contract, pending account state, frozen roster identity, row failures, and publication-time edit lock.
- [x] 10.4 Add post-publication invitation controls and per-recipient `not_sent`/`sent`/`failed` states, disable automatic/draft delivery, expose initial send plus failed-only resend, and poll/refetch roster state after the accepted scheduling response for final pending/error/success feedback.
- [x] 10.5 Update admin score, attendance, ranking, learning, and export surfaces to use frozen formal identity or account learning identity as appropriate and remove legacy fields and filters.
- [x] 10.6 Add focused frontend tests for upcoming invited exams, unscoped generic states, account lifecycle actions, roster freeze, initial invitation send, failed-only resend, report columns, accessible state announcements, and responsive admin tables/actions.

## 11. Legacy Cleanup, Seeds, And Documentation

- [x] 11.1 Remove sentinel creation/lookup and legacy candidate identity code from current models, schemas, services, routes, fixtures, factories, seeds, capacity gates, E2E setup, and runtime configuration while leaving historical migrations immutable.
- [x] 11.2 Remove current-code references to `employee_no`, `phone_suffix`, global `should_attend`, and global organization/personnel fields from backend/frontend contracts; permit them only in immutable historical migrations or explicitly labeled migration preflight fixtures.
- [x] 11.3 Update `README.md`, environment examples, API/database/import requirements, security notes, official-exam UAT, operations, and handoff documentation for email registration, immutable email, account states, reduced roster imports, frozen identity, invitations, rate limits, maintenance migration, and restore-only rollback.
- [x] 11.4 Update operational and browser E2E seeds so open registration, pending invitee, active scoped/unscoped user, inactive user, invitation outcomes, shared practice bank, and frozen-report identity can be exercised without legacy login fields.
- [x] 11.5 Add a repository-wide contract check that fails if removed runtime/API/UI/import/export field names or standalone candidate-import routes reappear outside approved historical migration and migration-test paths.

## 12. Verification, UAT, And OpenSpec Coordination

- [x] 12.1 Run backend format, lint, type, focused auth/import/invite/exam/report tests, the full disposable-PostgreSQL suite, and Alembic upgrade checks; resolve every regression before marking the backend complete.
- [x] 12.2 Run frontend format checks, Vitest, lint, and production build; verify the email-only, registration, profile, invitation, report, accessibility, and responsive contracts.
- [x] 12.3 Run browser E2E through Compose/Nginx with fake SMTP for new registration, existing login, invited pending account, shared practice, immediate upcoming-exam visibility, pre-open rejection, invitation send/failure/resend, frozen reports, deactivation, and session cleanup.
- [ ] 12.4 Verify Compose configuration, migrations from the current release, backend/frontend health, the fixed private-LAN candidate origin and loopback admin ingress with negative route/CORS checks, four-hour tokens, no third-party runtime, exact formal-writer identity/fence, and post-migration account/scope/attempt/report count invariants.
- [ ] 12.5 Execute controlled real-SMTP UAT for one OTP registration/login and one initial-plus-failed-resend invitation flow, confirming bounded retries, correct links, redacted logs, and no automatic publication mail.
- [ ] 12.6 Verify paired backup, independently stored encrypted second copy, isolated restore counts/checksums/migration-head/sample evidence, preflight, writer fence, and write freeze; rehearse restoring the previous release after the destructive boundary rather than relying on a fabricated downgrade.
- [x] 12.7 Re-read and rebase overlapping active/root specs so the obsolete early-login window and standalone candidate-import/write-gate contract do not reappear, refresh active-change ownership metadata, and prove that remaining Windows/macOS live-host gates are independent blockers not replaced by this change's local evidence.
- [ ] 12.8 Run `openspec validate open-email-registration-with-invited-exams --strict` and `openspec validate --all --strict`, resolve pre-existing or overlap-induced strict failures before archive, refresh handoff evidence with exact commands and residual external gates, and archive only after implementation verification confirms every requirement and task.
