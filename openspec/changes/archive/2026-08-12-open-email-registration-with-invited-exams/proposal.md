## Why

The current candidate login only sends an email OTP when name, roster email, and optional employee number already match an active candidate record, so people cannot create an account for learning, practice, or wrong-question review unless an administrator first places them in the personnel data. The platform now needs an email-first account boundary that is open to every valid mailbox reachable from the controlled LAN, except an existing account deliberately deactivated by an administrator, while preserving formal-exam access as an explicit per-exam invitation.

## What Changes

- **BREAKING** Replace roster-bound candidate lookup with one email-only OTP entry point for both login and registration. Existing active accounts log in after OTP verification; new and pending mailboxes receive a short-lived one-time registration-completion credential and must confirm a display name before receiving a four-hour `X-Candidate-Token`. A deliberately inactive account cannot register a replacement identity or log in until an administrator reactivates its completed account.
- Add a lightweight platform-account lifecycle with normalized case-insensitive unique email, independent display name, `pending`/`active`/`inactive` status, self-service display-name editing, and loopback-admin search plus activate/deactivate controls. Email changes and physical account deletion remain unavailable in the first phase.
- Preserve learning, shared-question-bank practice, immutable practice history, and wrong-question review for every authenticated active account. Formal and practice questions intentionally remain shared; formal exams continue drawing from the same frozen active bank.
- **BREAKING** Remove `employee_no`, `phone_suffix`, and global `should_attend` from persistence, schemas, APIs, imports, exports, UI, tests, and documentation after a verified pre-migration backup and conflict preflight.
- Move official exam identity and organization data to the per-exam scope: required normalized email and roster name, with optional department, position, exam group, and roster remark. Platform display-name changes must not rewrite published roster data or historical formal reports.
- Keep formal authorization invitation-only through `exam_candidate_scope`. Imports reuse accounts by normalized email or create non-login-capable pending accounts; publication freezes the roster; only scoped accounts may discover, start, resume, or read results for that exam.
- Add an explicit post-publication invitation-send action with per-recipient not-sent/sent/failed state and failed-only resend. Invitation email links preserve the target exam through login/registration but carry no bearer credential or authorization grant.
- Show a published invited exam immediately to its scoped user with its opening time, while continuing to reject attempt start before `available_from` and preserving the existing start grace, snapshot, attempt-session, draft recovery, submit, result-release, incident, and retake rules.
- Update the candidate frontend into a general user surface: “邮箱登录”, a separate first-registration profile step, an editable account profile, user-oriented terminology for learning/practice, invitation-aware exam states, and the confirmed login/OTP guidance.
- Keep the current controlled-LAN-only deployment, four-hour browser-session boundary, six-digit ten-minute single-use OTP, five verification attempts, sixty-second resend cooldown, and configurable per-email, per-source, and global send limits.

## Non-goals

- No public-Internet exposure, HTTPS/domain project, password login, SMS, SSO, passkeys, social login, or self-service email change.
- No invite codes, credential-bearing magic links, automatic exam access from email delivery, or roster edits after publication.
- No Redis, Celery, durable mail queue, microservice, complex RBAC, multi-tenancy, or full LMS/account-administration suite.
- No separate formal/practice question banks and no change to fixed-paper, scoring, attempt snapshots, answer-set comparison, result-release, retake, or reporting aggregation semantics except for roster identity fields.
- No automatic merge of legacy rows that share, omit, or contain an invalid email; migration must stop for operator resolution.
- No physical deletion of real `pending`, `active`, or `inactive` accounts. Removing the migration-only login sentinel is cleanup of a system placeholder, not an account-directory delete capability.

## Capabilities

### New Capabilities

- `platform-accounts`: Defines open email-OTP registration, profile completion, normalized unique identity, account lifecycle, administrator activation controls, and safe legacy-field migration.
- `exam-invitations`: Defines email-keyed per-exam roster identity, pending invitees, publication freeze, invitation delivery state, invitation links, immediate invited-exam visibility, and scope-only formal authorization.

### Modified Capabilities

- `candidate-access`: Changes roster-bound candidate login into a unified email-only login/registration challenge while preserving four-hour token gating, active-account enforcement, shared practice access, and strict per-exam authorization.
- `admin-imports`: Replaces employee/name reuse with normalized-email roster matching and a reduced exam-roster workbook contract while preserving bounded Excel validation and failure reports.
- `admin-reporting`: Uses frozen per-exam roster identity in formal reports and removes employee-number/phone/global-attendance fields without changing report scope or score aggregation.
- `frontend-page-experience`: Adds the unified email login/registration/profile journey, preserved invitation return paths, general-user versus exam-roster terminology, and invitation-aware loading/empty/error states.
- `video-learning`: Makes published learning videos and per-user progress available to every authenticated active platform account and replaces legacy personnel identity in learning reports with account identity.

## Impact

- Backend persistence and migration preflight: candidate/account columns and status, login challenges, `exam_candidate_scope` roster snapshots and invitation delivery metadata, unique normalized email enforcement, legacy scope backfill, and destructive-column removal after verified backup.
- Backend APIs/services/schemas: auth and registration completion, active-account dependencies, account profile/admin management, exam discovery/start/result authorization, roster import/publication, invitation email delivery, reports, learning/practice identity responses, audit events, and rate limits.
- Frontend: auth API and session state, login and registration-profile pages, account profile, candidate layout and terminology, invitation deep-link return handling, exam list/start states, admin account directory, roster import/table, reports, and focused accessibility behavior.
- Tests and operations: Alembic upgrade coverage, conflict preflight, backend auth/account/invite/report regressions, frontend Vitest and browser E2E, real SMTP invitation/OTP UAT, backup-before-migration evidence, OpenSpec validation, and README/API/database/import/exam-day/handoff documentation.
- Existing host portability, split ingress, controlled-LAN HTTP exception, no-third-party-runtime, backup/restore, single-device attempt, and formal release gates remain in force.
