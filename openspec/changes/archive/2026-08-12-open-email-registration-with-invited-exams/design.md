## Context

See `proposal.md` for the product motivation and approved scope. Today the `candidate` row is simultaneously a login identity, global personnel record, practice/learning owner, and formal-exam participant. Login challenges require a candidate FK and use a sentinel row for unknown identities; `exam_candidate_scope` contains only the exam/account join; reports read mutable candidate identity fields. The requested email-first registration and frozen per-exam roster identity therefore cross authentication, persistence, imports, reports, frontend routing, SMTP delivery, and destructive migration boundaries.

The repository already has important application-hardening changes in flight. This design preserves the effective live contracts from `stabilize-windows-internal-exam-platform`: four-hour candidate tokens, shared question-bank practice feedback, single-device attempt credentials, answer revisions and drafts, publication readiness, timing/grace rules, result-detail release, void/retake behavior, split ingress, and controlled-LAN operation. It does not use the stale root practice-response wording to regress the implemented answer-revealing practice flow.

## Goals / Non-Goals

**Goals:**

- Separate a general verified-email platform account from per-exam formal identity and authorization without rewriting every existing account-owned foreign key.
- Give every valid email a uniform, abuse-bounded OTP path while preventing incomplete or inactive accounts from receiving a candidate token.
- Make account deactivation effective on the next authenticated request, including an in-progress attempt, while preserving the attempt for explicit recovery or voiding.
- Freeze official roster identity per exam so profile edits and later organization changes cannot rewrite formal reports.
- Deliver a destructive legacy-field migration that fails closed on unsafe data and has a truthful restore-based rollback boundary.
- Keep the implementation inside the existing FastAPI/PostgreSQL/React single-host architecture with no new service or durable queue.

**Non-Goals:**

- Renaming every `candidate_id` foreign key, token subject, or internal module to `account` in this change.
- Making invitation email delivery exactly once; the lightweight sender is recoverable and auditable but may be at-least-once around an SMTP-success/database-failure boundary.
- Replacing the existing operator authentication model or host-portability work. “Admin account management” means administrators manage platform user accounts through the existing loopback-only, token-protected admin surface.
- Changing the existing archive/retention workflow. The account directory has no delete action; existing preview/archive/verified-backup retention controls remain authoritative for eligible historical data.

## Decisions

### 1. Retain the candidate primary key as the compatibility account identity

The existing `candidate` table, primary key, `candidate_id` foreign keys, and `candidate:<id>` token subject remain the persistence compatibility shell. The row's meaning changes to a platform account:

- normalized immutable `email` is required and unique;
- the existing physical `name` column is treated as the editable platform display name and may be nullable only while status is `pending`;
- status becomes `pending`, `active`, or `inactive`;
- `employee_no`, `phone_suffix`, `department`, `position`, `exam_group`, `should_attend`, `remark`, and `is_login_sentinel` are removed after backfill;
- API and visible frontend terminology use account/user and `display_name`, even if the compatibility table and some internal IDs retain candidate naming.

An active row MUST have a non-empty display name. A pending row exists only to attach a pre-registration email to one or more exam scopes and cannot receive `X-Candidate-Token`. An inactive row remains unique for its email, cannot be re-registered as a duplicate, and keeps its histories and scopes.

Creating a separate account table was rejected because it would require migrating every attempt, practice answer, learning progress, retake, report, audit, and session relationship. Renaming the table and all IDs was rejected as a large semantic refactor with no user-visible benefit in this phase.

### 2. Normalize email once and enforce the same invariant in PostgreSQL

Application input uses `trim` plus lowercase normalization after email syntax validation. The system does not collapse plus-addresses, remove dots, or apply provider-specific alias rules. Persisted account email and roster email use the normalized value. A database unique constraint/index protects the account email independently of service validation, and a constraint prevents non-normalized persisted values.

Legacy null, invalid, or case-insensitive duplicate emails are migration blockers. The system does not infer identity from name, employee number, phone suffix, department, or practice/exam history and does not auto-merge rows.

### 3. Use one OTP challenge state machine for existing, pending, and new emails

The public API retains the existing route family to limit client and ingress churn:

| Action | Endpoint | Result |
|---|---|---|
| Request OTP | `POST /api/candidates/login` | Uniform challenge envelope for a syntactically valid email |
| Verify OTP | `POST /api/candidates/login/verify` | Discriminated `authenticated` or `registration_required` result |
| Complete registration | `POST /api/candidates/register/complete` | Active account plus four-hour candidate token |
| Read/update profile | `GET/PATCH /api/account/profile` | Display name is editable; email is read-only |

`CandidateLoginChallenge` is changed from a required sentinel/candidate association to a normalized-email challenge with an optional account association. It stores the OTP verifier, expiry, consumption and attempt metadata, request-source hash, and optional hashed one-time registration-completion credential. Plain OTPs, completion credentials, tokens, and SMTP credentials are never persisted or logged.

The flow is:

1. Validate and normalize email, apply per-source, per-email, and global limits, invalidate earlier open challenges for that email, persist the new challenge, then schedule bounded OTP delivery.
2. If the email belongs to an active account, a correct OTP atomically consumes the challenge and returns the normal account/token result.
3. If the email belongs to a pending account or no account, a correct OTP atomically consumes the OTP and returns a short-lived one-time registration-completion credential. It does not yet create an active account or issue a candidate token.
4. Registration completion validates and consumes the credential in one transaction, confirms a non-empty display name, creates or activates the normalized-email account, and issues the token. A pending invite's most recently created eligible roster name may be returned as a suggestion, but the user must explicitly confirm or edit it.
5. If the email belongs to an inactive account, the challenge response and actual OTP delivery remain uniform. A correct OTP proves mailbox control and is consumed, but verification returns a stable account-unavailable outcome with no registration credential or token; an administrator must reactivate the completed account before a later challenge can authenticate it.

A uniqueness race during registration completion is resolved inside the transaction by reloading the winning normalized-email row. The operation never overwrites an existing active account's display name.

The registration-completion credential is random, stored only as a hash, expires no later than the OTP lifetime, and is single-use. Expired challenge and completion rows are removed through bounded opportunistic cleanup and the existing lifecycle tooling, not a new worker service.

### 4. Centralize active-account enforcement without changing token shape

Token signature and four-hour lifetime remain unchanged. The shared candidate dependency must parse the token, load its account, and require `status=active` on every candidate-facing request. Routes may still receive `candidate_id` for service compatibility, while services retain defense-in-depth ownership/status checks.

This dependency applies to learning, practice, wrong-question review, exam discovery/start, attempt read/save/submit/result/takeover, and profile APIs. Deactivation therefore takes effect on the next request even for a still-valid token and current attempt-session credential. It does not mutate the attempt: an operator must reactivate the account for remaining-time continuation or use the existing incident/void workflow. The server-side auto-submit worker remains able to process an overdue attempt because it does not authenticate as the user.

Formal authorization remains an independent scope check. A valid active-account token without the relevant `exam_candidate_scope` cannot discover, start, resume, take over, or read a result for that exam. Learning and shared-bank practice require only an active account and do not create formal eligibility.

### 5. Make exam scope the immutable source of formal identity

`exam_candidate_scope` keeps the unique `(exam_id, candidate_id)` relationship and adds:

- required normalized `roster_email` and `roster_name`;
- optional `department`, `position`, `exam_group`, and `roster_remark`;
- invitation delivery status and non-secret attempt timestamps/error classification;
- internal delivery-claim metadata used to prevent concurrent duplicate scheduling.

The account email is immutable, but `roster_email` is still stored as a formal snapshot so historical exports do not depend on a mutable join contract. The database enforces both one scope per `(exam_id, candidate_id)` and one normalized roster email per exam. Draft roster imports match or create a pending account by normalized email and populate only scope-owned fields; they never overwrite an active account display name or status. An inactive account is a row-level import conflict until an administrator deliberately reactivates it. Removing a draft scope preserves the account. Publishing revalidates required scope fields and freezes the roster in the same authoritative publication boundary that freezes the question pool. Published scopes cannot be added, edited, or removed.

This new `exam-invitations` capability owns roster freeze and invitation readiness. It integrates with, but does not redefine, the existing fixed-paper and attempt-snapshot requirements in `exam-delivery`.

### 6. Keep invitations notification-only and use a recoverable in-process sender

Invitation email never grants access. The administrator first publishes the ready exam, then explicitly requests initial delivery for `not_sent` scopes. A separate failed-only action retries `failed` scopes. Both are protected by the existing admin token, loopback ingress, audit service, operational write gates, and a per-action batch cap.

The service row-locks selected scopes and records a short-lived claim before adding an in-process background delivery task. The mutation response reports only accepted/rejected selection counts; the roster-status query and protected audit records expose final per-recipient outcomes after background processing. Each recipient is processed independently with a new database session and the existing bounded SMTP retry adapter, using the frozen scope `roster_email` as the invitation recipient:

- success records `sent` and the send timestamp;
- exhausted/permanent failure records `failed` plus a sanitized error class;
- a process interruption leaves a stale claim on `not_sent` or `failed`, which the next explicit send can recover after the configured stale threshold.

There is no Celery/Redis/durable mail queue and no automatic endless retry. SMTP can succeed immediately before the status commit fails, so an operator retry can produce a duplicate message; a deterministic message identifier and audit metadata reduce diagnosis cost but cannot guarantee exactly-once delivery.

Invitation URLs are built from the single configured private-LAN candidate origin and an allowlisted exam route. They carry no OTP, candidate token, invite code, scope identifier, email, or authorization secret. The frontend preserves the same-origin `returnTo` path through OTP verification and registration completion, then loads the exam through normal token/scope checks. Invalid or unscoped access uses a generic unavailable state.

### 7. Preserve exam timing while making scoped published exams visible immediately

Login is platform-wide and no longer opens only near a formal exam. An active scoped user may see a published exam immediately, including `not_started` availability and the exact opening time. Attempt start continues to reject requests before `available_from`, after the configured start grace, or after other existing eligibility boundaries. In-progress resume, device takeover, snapshots, scoring, submission, detail release, voiding, and retakes are unchanged.

This behavior supersedes the active change's older “early candidate login window” rationale while preserving its start-time prohibition and four-hour token rule. The overlapping active change artifacts are coordinated in the same working tree so the obsolete window cannot reappear during a later archive; see OpenSpec coordination below.

### 8. Read formal reports from frozen scope identity

Formal score, attendance, incident, retake, evidence, ranking, and Excel rows obtain roster name/email/organization fields from the exam scope associated with each exam/account pair. Account profile updates and deactivation cannot rewrite those values or remove historical results. Existing exam filters, latest-attempt attendance classification, void exclusions, score calculations, workbook layout, and formula escaping remain intact.

Learning reports use account email/display name/status because learning is not exam scoped. They no longer expose removed employee, phone, global attendance, or global organization fields. The existing retention workflow may archive eligible history through its guarded process, but the new account directory exposes no delete operation.

### 9. Keep the frontend session model but add explicit auth-flow state

The full candidate token/account payload remains in session-scoped browser storage and expires server-side after four hours; there is no remember-me state. The OTP challenge and registration-completion credential are held in the auth flow only and are never treated as candidate credentials by the shared API client.

The login route renders email request then OTP verification. An `authenticated` response stores the account session; `registration_required` navigates to a profile-completion route that preserves the validated same-origin return path. The candidate layout captures the original path before redirecting to login, including invitation links, and clears account, attempt-session, and draft state on logout, token expiry, or inactive-account 401.

The new profile page edits display name only. Top navigation and ordinary learning/practice copy use “用户”; formal roster and exam contexts use “应考人员”. Login copy uses the exact strings approved in the specs. All new forms, status views, tables, and mobile states reuse the existing Academic Editorial primitives and accessibility contracts.

### 10. Enforce abuse limits from persisted challenge evidence plus a burst guard

The existing in-memory limiter remains a cheap burst guard, but normalized-email, request-source-hash, and global OTP send windows are also evaluated from persisted challenge metadata so process restart or multiple backend workers cannot reset the policy. Configuration supplies the per-window thresholds and global daily ceiling; six digits, ten-minute expiry, five verification attempts, and sixty-second resend cooldown retain their approved defaults. Invitation delivery uses separate admin-only batch limits and does not consume public-login quotas.

Logs and audit events contain challenge/scope IDs, counts, status, operator, and hashed request-source data only. They exclude plaintext submitted email, OTP, completion credentials, candidate tokens, SMTP credentials, and invitation URLs containing user-specific data.

### 11. Coordinate with overlapping active OpenSpec changes explicitly

`stabilize-windows-internal-exam-platform` currently carries application requirements that are already implemented even though its host-acceptance tasks remain open. This change preserves those effective contracts and intentionally supersedes only roster-bound login timing/identity behavior, including its obsolete 30-minute login-opening window while retaining the start-time gate. `support-macos-formal-host-portability` continues to own the selected formal-host and writer/cutover contract.

Do not archive this change mechanically over another active delta that owns the same capability. Before archive, re-read the then-current root and active specs and rebase the `candidate-access`, `admin-imports`, `admin-reporting`, and `frontend-page-experience` deltas so both the stabilized application contracts and this change survive. Host acceptance evidence from either platform does not count as implementation evidence for this account/invitation change, and vice versa.

## Risks / Trade-offs

- [Destructive legacy-column removal can make the old release unreadable] → Require verified paired backup, conflict preflight, maintenance/write freeze, explicit post-migration verification, and restore-based rollback rather than claiming a lossless Alembic downgrade.
- [Legacy null, malformed, or duplicate emails make identity ambiguous] → Block before mutation, emit a non-secret conflict report, and require operator resolution; never merge by name or personnel fields.
- [Scope backfill errors can rewrite formal identity] → Populate every existing scope from its pre-drop candidate row, ensure attempts have a scope, compare counts/checksums, and stop before dropping source fields if any row cannot be backfilled.
- [Account deactivation during an exam interrupts saves] → Make the effect explicit, retain the attempt and server auto-submit behavior, and use reactivation or the existing void/retake incident workflow.
- [In-process invitation delivery can be interrupted or duplicated] → Persist claims and per-recipient outcomes, recover stale claims only through explicit operator action, cap batches, use deterministic message identifiers, and document at-least-once behavior.
- [Any valid email can be used to send mail] → Keep the candidate gateway LAN-only, use persisted per-email/source/global limits, uniform responses, bounded SMTP retry, redacted audit, and real-SMTP UAT.
- [Profile and roster names can diverge] → Make the distinction visible, prefill but require confirmation for new accounts, and always use frozen roster identity for formal outputs.
- [Shared practice/formal questions expose answers before an exam] → This is an explicitly accepted product choice; preserve the shared bank and do not imply question secrecy in security or UAT claims.
- [Overlapping active OpenSpec deltas can archive in the wrong order] → Treat archive as a rebase/merge step, preserve capability ownership, and validate the final effective specs before archiving.

## Migration Plan

1. Add a read-only preflight that excludes the designated sentinel from real-account checks and reports: missing/invalid/non-normalized/duplicate real emails, sentinel contamination, missing scopes for historical attempts, and scope rows that cannot receive roster snapshots. It makes no repair or merge.
2. Create and verify a paired PostgreSQL/media backup plus the independently stored encrypted second copy under the existing formal-host workflow. Complete an isolated restore with counts, checksums, migration head, and representative samples. Record only the backup/evidence references in the maintenance checklist; do not place secrets or data extracts in the repository.
3. Enter a maintenance window on the currently selected Mac formal writer, validate the exact `datasetId`/`hostId`/`writerGeneration` whole-project fence, stop candidate traffic and background writes on every source/target host, acquire the operational write freeze, and confirm no attempt is in progress. Windows-host evidence cannot satisfy this selected-writer gate.
4. Apply an additive/backfill migration only after the read-only preflight proves every historical attempt already has an operator-reviewed scope: expire outstanding login challenges; add new challenge/account-status/scope/invitation fields; normalize valid real-account emails; backfill every existing scope's roster snapshot; and verify row/count invariants. A missing historical scope remains a blocker for explicit operator repair and is never synthesized inside the destructive migration.
5. Apply the destructive migration step: detach and delete the login sentinel, enforce normalized unique non-null account email and active-display-name constraints, then drop sentinel and legacy personnel/global-attendance columns, indexes, and constraints.
6. Deploy the backend/frontend that understands the new schema, run migration and API smoke checks, verify account/profile/roster/report counts, then release the write freeze.
7. Run focused fake-SMTP E2E plus one real-SMTP OTP and invitation delivery UAT before formal use. Confirm a profile edit does not alter frozen roster/report values and deactivation blocks all candidate endpoints without deleting an attempt.
8. If failure occurs before destructive migration, roll back the release normally after releasing the maintenance lock. If failure occurs after destructive migration, stop all writers and restore the verified paired backup with the previous release; do not use a downgrade that fabricates deleted employee/phone/attendance data. Any post-backup writes require the existing exact data-loss confirmation boundary.

## Open Questions

None. Product decisions that affect observable behavior were resolved during the grilling session; implementation-only constants remain configurable within the specified boundaries.
