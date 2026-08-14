## Purpose

The admin exam workspace provides a privacy-bounded, exam-scoped lifecycle summary so an operator can identify the current state and the next safe action without reconciling several pages manually.

## ADDED Requirements

### Requirement: Admin-Only Exam Workspace
The system SHALL provide an admin-authenticated read operation for one exam workspace at `/api/admin/exams/{exam_id}/workspace`. The response MUST identify the exam, capture one server observation time, and omit roster names, email addresses, and other row-level identity data.

#### Scenario: Authenticated administrator opens a workspace
- **WHEN** an authenticated administrator requests an existing exam workspace
- **THEN** the system returns the exam lifecycle summary and `observed_at`
- **AND** the response contains aggregate counts rather than roster PII

#### Scenario: Unauthenticated caller requests a workspace
- **WHEN** a caller without a valid admin session requests an exam workspace
- **THEN** the system rejects the request under the existing admin authorization contract

#### Scenario: Administrator requests a missing exam
- **WHEN** an authenticated administrator requests a workspace for an exam that does not exist
- **THEN** the system returns the existing exam-not-found outcome instead of an empty workspace

### Requirement: Reconciled Lifecycle Summaries
The workspace SHALL return publication readiness for a draft exam and aggregate roster, invitation, attendance, attempt, and incident summaries. Attendance MUST use the latest attempt number for each frozen scope, treat `submitted` and `auto_submitted` as submitted, and treat a latest `voided` attempt as not started; raw attempt counts MUST remain separately available.

#### Scenario: Draft exam is inspected
- **WHEN** an administrator opens a draft exam workspace
- **THEN** the response includes current publication readiness and its blocker codes
- **AND** it reports roster and account-state counts before publication

#### Scenario: Published exam has mixed delivery and attempt states
- **WHEN** a published exam contains unsent, sending, sent, and failed invitations together with initial and retake attempts
- **THEN** invitation counts distinguish `not_sent`, `sent`, `failed`, and `in_flight`
- **AND** attendance counts use each scoped account's latest attempt
- **AND** raw attempt counts distinguish `in_progress`, `submitted`, `auto_submitted`, and `voided`

#### Scenario: Latest retake was voided
- **GIVEN** a scoped account has an older submitted attempt and a newer voided retake
- **WHEN** the workspace aggregates attendance
- **THEN** that account is counted as not started under the existing attendance-report rule
- **AND** the voided attempt remains visible in the raw attempt and incident summaries

### Requirement: Advisory Next Action
The workspace SHALL return exactly one advisory `next_action` and a user-facing reason derived from the observed lifecycle state. The value MUST NOT authorize or bypass any write endpoint; every mutation MUST revalidate its own current preconditions.

#### Scenario: Draft exam has no roster
- **WHEN** a draft exam has no roster rows
- **THEN** the next action is `manage_roster`

#### Scenario: Draft exam is not ready or is ready
- **WHEN** a draft exam has publication blockers
- **THEN** the next action is `fix_readiness`
- **WHEN** the draft exam has a roster and publication readiness passes
- **THEN** the next action is `publish`

#### Scenario: Invitation delivery needs attention
- **WHEN** a published exam has an invitation claim in flight
- **THEN** the next action is `wait_invitation_delivery`
- **WHEN** no claim is in flight and at least one invitation is not sent
- **THEN** the next action is `send_invitations`
- **WHEN** no claim is in flight or unsent and at least one invitation failed
- **THEN** the next action is `resend_failed_invitations`

#### Scenario: Published exam progresses through delivery
- **WHEN** invitation delivery is settled and the exam has not opened
- **THEN** the next action is `wait_for_open`
- **WHEN** an attempt is in progress or an open exam is awaiting candidates
- **THEN** the next action is `monitor_exam`
- **WHEN** no attempt is in progress and only voided or no usable submissions remain after the exam window
- **THEN** the next action is `review_incidents`

#### Scenario: Results can be released or exam can be archived
- **WHEN** no attempt is in progress, at least one usable submission exists, and details are not released
- **THEN** the next action is `release_result_details`
- **WHEN** result details are released and the exam is still active
- **THEN** the next action is `archive_exam`
- **WHEN** the exam is archived
- **THEN** the next action is `complete`

### Requirement: Workspace Refresh Is Bounded
The admin frontend SHALL refresh an active exam workspace at a bounded interval while live state can change, stop background polling for an archived exam, and invalidate the workspace immediately after a successful exam-scoped mutation.

#### Scenario: Active workspace remains open
- **WHEN** an administrator keeps an active exam workspace open
- **THEN** summary data refreshes no more frequently than once every fifteen seconds
- **AND** the page shows the server observation time

#### Scenario: Exam becomes archived
- **WHEN** a workspace refresh reports that the exam is archived
- **THEN** periodic background refresh stops

#### Scenario: Administrator completes a linked action
- **WHEN** a successful publish, invitation, result-release, retake, void, or archive action affects the exam
- **THEN** the frontend invalidates the exam workspace query so the next view does not rely on the previous advisory action

