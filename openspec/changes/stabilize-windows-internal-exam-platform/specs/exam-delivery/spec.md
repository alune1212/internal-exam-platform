## MODIFIED Requirements

### Requirement: Answer Save And Submit
The system SHALL save answers during an in-progress attempt and SHALL score submitted attempts from snapshot data. Save and submit requests MUST carry the current attempt-session credential and answer revision so stale devices cannot silently overwrite newer server state.

#### Scenario: Candidate saves an answer
- **GIVEN** an in-progress attempt, current attempt-session credential, and current answer revision
- **WHEN** the candidate saves answers
- **THEN** the system persists the current answers without pausing the countdown
- **AND** returns the next answer revision and server save time

#### Scenario: Candidate saves with a stale revision
- **GIVEN** the server has a newer answer revision or attempt-session generation
- **WHEN** an older device sends a save
- **THEN** the system rejects the stale write with a conflict response
- **AND** does not overwrite the newer answers

#### Scenario: Candidate submits attempt
- **GIVEN** an in-progress attempt with current session ownership and saved or submitted answers
- **WHEN** the candidate submits the attempt manually
- **THEN** the system serializes save and submit, scores answers against snapshot correct answers, and records pass status from the exam rule

#### Scenario: Pending browser draft is not accepted by server
- **GIVEN** a browser has selections that have not reached the backend
- **WHEN** the connection remains unavailable
- **THEN** those selections do not change server scoring or constitute a submitted attempt

## ADDED Requirements

### Requirement: Formal Exam Timing Boundary
New or updated formal exams MUST have `duration_minutes` no greater than 120. Candidate login SHALL open 30 minutes before `available_from`, and new attempt starts SHALL close 15 minutes after `available_from`; a candidate starting within the grace period SHALL receive the full configured duration.

#### Scenario: Operator configures a valid formal window
- **WHEN** a formal exam uses a duration of at most 120 minutes and a start cutoff 15 minutes after `available_from`
- **THEN** publication timing validation accepts the configuration

#### Scenario: Operator exceeds formal limits
- **WHEN** a new or updated formal exam exceeds 120 minutes or its start grace exceeds 15 minutes
- **THEN** publication readiness reports a blocker and publishing is rejected

#### Scenario: Candidate starts within grace
- **GIVEN** the current time is at or after `available_from` and no more than 15 minutes later
- **WHEN** an eligible candidate starts
- **THEN** the attempt deadline is its `started_at` plus the full configured duration

#### Scenario: Candidate starts after cutoff
- **WHEN** an eligible candidate without an in-progress attempt starts more than 15 minutes after `available_from`
- **THEN** the system rejects new attempt creation

### Requirement: Publication Readiness And Confirmation
The system MUST provide a publication-readiness result covering deduplicated question inventory, fixed-paper type/category coverage, score rules, duration/window limits, roster/email readiness, and frozen-pool count. Publishing MUST require the exact exam title and MUST rerun authoritative blockers transactionally.

#### Scenario: Draft has blockers
- **WHEN** publication readiness finds insufficient unique stems, type/category coverage, invalid score/timing rules, or unusable roster emails
- **THEN** it returns explicit blockers
- **AND** publishing cannot activate or freeze the exam

#### Scenario: Operator confirms a ready draft
- **GIVEN** readiness has no blocker and the operator enters the exact exam title
- **WHEN** the publish request runs
- **THEN** the service revalidates readiness in the publish transaction
- **AND** activates the exam and freezes the pool only if the checks still pass

#### Scenario: Confirmation title is wrong
- **WHEN** the submitted confirmation does not exactly match the draft exam title
- **THEN** publishing is rejected without changing exam status or pool

### Requirement: Formal Attempt Admin Write Protection
While any formal attempt is `in_progress`, the system MUST reject non-essential administrator mutations that could consume resources or change exam-supporting state, while preserving health, operational views, reports, formal answer save, and submit.

#### Scenario: Operator attempts a prohibited mutation during an exam
- **WHEN** an operator imports questions or candidates, changes roster or exam configuration, publishes an exam, uploads or changes video state, or performs another protected mutation while an attempt is in progress
- **THEN** the service rejects the mutation with a stable conflict response

#### Scenario: Operator reads state during an exam
- **WHEN** the operator opens health, operations, monitoring, or report views during an in-progress exam
- **THEN** the read remains available

### Requirement: Recoverable Pending Answer Draft
The exam client SHALL keep unsynchronized selections in session-scoped browser storage tied to candidate, attempt, attempt-session generation, and answer revision. It MUST retry after connectivity returns and MUST clear the draft after successful submission.

#### Scenario: Save fails after a selection
- **WHEN** a network failure prevents the latest answer save
- **THEN** the page displays an offline or pending-sync state
- **AND** keeps the current pending selections in session-scoped storage

#### Scenario: Candidate reloads the same active session
- **GIVEN** a matching pending draft and no newer conflicting server revision
- **WHEN** the page reloads
- **THEN** it restores the pending selections and retries synchronization

#### Scenario: Local draft is stale or belongs to another session
- **WHEN** the stored draft does not match the active candidate, attempt-session generation, or server revision
- **THEN** it is not automatically written over newer server state

#### Scenario: Candidate is offline at submission
- **WHEN** the candidate attempts final submission without server connectivity
- **THEN** submission does not claim success
- **AND** the page preserves the pending draft and shows a retry instruction while the server deadline continues

### Requirement: One-Time Result Detail Release
New formal exams SHALL show candidates their score and pass status after submission but MUST withhold correct-answer and analysis snapshots until an administrator performs an irreversible one-time release after all attempts are terminal. Candidate ranking MUST remain unavailable.

#### Scenario: Candidate submits before detail release
- **WHEN** a candidate opens a terminal attempt result before release
- **THEN** the result includes score and pass status
- **AND** omits correct answers, analysis, and candidate ranking

#### Scenario: Operator releases details too early
- **GIVEN** at least one attempt is in progress
- **WHEN** result-detail release is requested
- **THEN** the system rejects the operation

#### Scenario: Operator releases details after completion
- **GIVEN** every attempt is terminal and release has not occurred
- **WHEN** the operator confirms release
- **THEN** the exam records release time and operator
- **AND** candidate results may return correct-answer and analysis snapshots from each attempt

#### Scenario: Operator attempts to retract or repeat release
- **GIVEN** result details were already released
- **WHEN** a retract or second release is requested
- **THEN** the application rejects the state change

### Requirement: Voided Attempt Incident Semantics
The system SHALL support a terminal `voided` attempt status with timestamp, operator, and reason. Voiding MUST preserve snapshots, answers, timing, and audit evidence, MUST exclude the result from normal score/ranking/pass aggregates, and MUST prevent auto-submit from processing it.

#### Scenario: Operator voids an affected attempt
- **GIVEN** an evidenced exam incident and an eligible attempt
- **WHEN** the operator confirms voiding with a reason
- **THEN** the attempt becomes terminal `voided`
- **AND** its historical data remains available in incident views

#### Scenario: Worker encounters a voided attempt
- **WHEN** auto-submit scans a voided attempt after its original deadline
- **THEN** it does not submit, score, or change the attempt

### Requirement: Audited Bulk Retake Recovery
The system SHALL preview and apply one-use retake grants for selected incident-affected candidates in a single audited operation. It MUST skip ineligible, duplicate, or already-granted rows and return a row-level outcome report.

#### Scenario: Operator grants incident retakes
- **GIVEN** a preview identifies eligible affected attempts
- **WHEN** the operator confirms the explicit selection
- **THEN** the system creates at most one unused retake grant per eligible candidate
- **AND** returns granted and skipped outcomes and writes an audit event

#### Scenario: Host failure interrupts an exam
- **WHEN** the operator determines that the outage exceeds the accepted short interruption
- **THEN** the runbook stops or reschedules the exam and uses void/bulk-retake recovery
- **AND** the system does not pause every attempt clock, edit scores, or perform automatic failover
