## Purpose

Defines the per-exam roster, publication freeze, invitation delivery, and scope authorization boundary for formal exams. Roster identity is keyed by normalized email while the account lifecycle remains separate from the frozen identity shown in formal exam records.

## ADDED Requirements

### Requirement: Email-Keyed Invitation Scope

The system SHALL represent each formal exam invitee in `exam_candidate_scope` by a normalized, case-insensitive email and SHALL associate that scope with the matching platform account when one exists. An import MAY reuse an active or pending account, or create a pending account for a new email; a pending account MAY use only the short-lived registration-completion flow and MUST NOT receive a candidate token or formal access until registration is completed. An inactive account is a row-level conflict until an administrator reactivates it. Database and transaction constraints MUST allow at most one scope row for each normalized email and exam.

#### Scenario: New email becomes a pending invitee

- **GIVEN** an exam is still a draft and no platform account exists for the normalized roster email
- **WHEN** an administrator adds the email to the exam roster
- **THEN** the system creates a pending account and an exam scope row keyed by that email
- **AND** the pending account cannot receive a candidate token, discover, start, or read results for the exam until registration is completed

#### Scenario: Existing account is reused case-insensitively

- **GIVEN** an active or pending account already uses the normalized form of a roster email
- **WHEN** an administrator adds that email to the exam roster with different casing or surrounding whitespace
- **THEN** the system reuses the existing account and creates at most one scope row for the exam
- **AND** it does not create a second account for the alternate spelling

#### Scenario: Duplicate email is added to one exam

- **GIVEN** an exam already has a scope row for a normalized email
- **WHEN** the same normalized email is added again
- **THEN** the system keeps one scope row and reports the duplicate without granting additional access

#### Scenario: Inactive email is imported

- **GIVEN** a completed platform account for the normalized roster email is `inactive`
- **WHEN** an administrator imports that email into a draft exam roster
- **THEN** the row fails with an account-reactivation reason
- **AND** the system creates neither a duplicate account nor an exam scope

### Requirement: Frozen Roster Identity And Draft Editing

Draft exam rosters SHALL be editable by an authenticated administrator: rows may be added, updated, or removed before publication. Each row MUST store required `roster_name` plus optional `department`, `position`, `exam_group`, and `remark`. Publication SHALL atomically freeze those roster fields and the associated scope set; published rows MUST NOT be edited or removed. Later platform display-name changes MUST NOT rewrite frozen roster identity or historical formal reports.

#### Scenario: Administrator edits a draft roster

- **GIVEN** an exam is in draft status
- **WHEN** an administrator adds, edits, or removes a roster row
- **THEN** the draft reflects the change in its `exam_candidate_scope` data
- **AND** no invitation is sent solely because the draft was edited

#### Scenario: Publication freezes the roster

- **GIVEN** a draft exam has a valid roster and is ready to publish
- **WHEN** the administrator publishes the exam
- **THEN** the publication transaction freezes the roster names and optional organization fields
- **AND** later roster mutations are rejected without changing the published scope

#### Scenario: Display name changes after publication

- **GIVEN** an account has a published exam scope with a frozen `roster_name`
- **WHEN** the account changes its platform display name after registration
- **THEN** the account profile uses the new display name
- **AND** the exam scope and formal reports continue to use the frozen `roster_name` and organization fields

### Requirement: Explicit Invitation Delivery State

Publishing an exam MUST NOT send invitations automatically. After publication, an authenticated administrator SHALL explicitly start invitation delivery. Every published scope row MUST expose a delivery state of `not_sent`, `sent`, or `failed`; a send attempt MUST record the per-recipient outcome without changing the frozen roster. A resend operation MUST target failed rows only.

#### Scenario: Published exam starts with unsent invitations

- **GIVEN** an exam is published with one or more scoped accounts
- **WHEN** publication completes
- **THEN** every recipient has delivery state `not_sent`
- **AND** no invitation email is sent until the administrator invokes the explicit send action

#### Scenario: Explicit send schedules per-recipient delivery

- **GIVEN** a published exam has `not_sent` recipients
- **WHEN** the administrator invokes the invitation-send action
- **THEN** the action response reports accepted and rejected selection counts without claiming final SMTP outcomes
- **AND** subsequent roster-status queries show each attempted recipient as `sent` after success or `failed` after exhausted delivery
- **AND** protected audit records identify final counts and non-secret failure classes without exposing credentials

#### Scenario: Failed-only resend

- **GIVEN** a published exam has both `failed` and `sent` invitation rows
- **WHEN** the administrator requests a resend
- **THEN** the system attempts delivery only for the `failed` rows
- **AND** a successful retry changes that row to `sent` while existing `sent` rows are not resent or downgraded

#### Scenario: Invitation mutation is blocked by the formal write gate

- **GIVEN** a formal attempt is in progress or the coordinated backup freeze is active
- **WHEN** an administrator requests initial invitation send or failed-only resend
- **THEN** the system rejects the mutation without claiming recipients or scheduling email
- **AND** existing delivery states remain unchanged

### Requirement: Bearer-Free Invitation Links

An invitation email MAY include a link that preserves the target exam through the login or registration flow, but the link MUST contain no bearer token, OTP, credential, or authorization grant. The target exam context MUST remain subject to successful email authentication, registration completion, account status, and the frozen exam scope.

#### Scenario: Link opens the target exam login flow

- **GIVEN** an invitation email contains a target-exam link
- **WHEN** an unauthenticated recipient opens the link
- **THEN** the application preserves the target exam while presenting the normal email OTP login or registration flow
- **AND** the link alone does not issue a token or reveal formal exam data

#### Scenario: Link is opened without matching scope

- **GIVEN** a user authenticates from an invitation link but has no active account scope for the target exam
- **WHEN** the user follows the preserved target exam context
- **THEN** the system denies formal discovery and access
- **AND** it does not convert the email delivery into an authorization grant

#### Scenario: Invitation URL is copied to another browser

- **GIVEN** a recipient copies an invitation URL before authenticating
- **WHEN** another person opens that URL
- **THEN** the second person still must authenticate with their own email OTP and satisfy scope authorization
- **AND** the URL does not function as a bearer credential

### Requirement: Immediate Scoped Exam Visibility And Opening Boundary

Once an exam is published, an active account with a matching frozen scope SHALL see that exam immediately, regardless of whether its invitation has been sent, together with the server-provided `available_from` opening time and current availability state. The candidate MUST NOT start a new attempt before `available_from`; the existing start-grace, full-duration, resume, snapshot, and submit rules remain authoritative after opening.

#### Scenario: Scoped account sees a published exam before invitation send

- **GIVEN** an exam is published and the account is active and in its frozen scope
- **AND** the invitation delivery state is `not_sent`
- **WHEN** the account requests active exams
- **THEN** the response includes the exam immediately with its opening time and not-yet-open state

#### Scenario: Candidate starts before opening

- **GIVEN** an active scoped account requests a new attempt before `available_from`
- **WHEN** the candidate calls the exam-start operation
- **THEN** the system rejects the start without creating an attempt

#### Scenario: Candidate starts during the existing grace period

- **GIVEN** the current time is at or after `available_from` and within the configured start grace
- **WHEN** an active scoped candidate starts the exam
- **THEN** the system creates the attempt under the existing full-duration and snapshot rules

### Requirement: Scope-Only Formal Authorization

Formal exam discovery, start, resume, attempt reads, result reads, and retake operations MUST require an active authenticated account whose normalized email matches the exam's frozen scope. An active account without that scope, a pending account, and an inactive account MUST be denied even if they possess a target-exam URL or know the exam identifier.

#### Scenario: Scoped active account uses formal APIs

- **GIVEN** an active account has a frozen scope row for a published exam
- **WHEN** it requests the exam list, starts or resumes an attempt, or reads an authorized result
- **THEN** scope authorization succeeds subject to timing, attempt, and result-release rules

#### Scenario: Active account is not in the exam scope

- **GIVEN** an active account has no scope row for a published exam
- **WHEN** it requests discovery, start, resume, attempt, or result data for that exam
- **THEN** the system rejects the request and returns no formal exam data

#### Scenario: Pending or inactive account has a scope row

- **GIVEN** a pending or inactive account is present in an exam scope
- **WHEN** it requests a formal exam API
- **THEN** the system denies the request without issuing or accepting a candidate session token
