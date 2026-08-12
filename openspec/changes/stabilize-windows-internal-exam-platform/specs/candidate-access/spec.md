## MODIFIED Requirements

### Requirement: Practice API Privacy
The system MUST require `X-Candidate-Token` for practice APIs and MUST omit correct answers and analysis before a practice submission. After an authenticated candidate submits one answer, the response SHALL reveal that submission's correctness, normalized correct answer, analysis, and selected-versus-correct option comparison.

#### Scenario: Candidate lists practice questions
- **GIVEN** a valid candidate token
- **WHEN** the candidate requests practice questions
- **THEN** the response omits correct answers and analysis

#### Scenario: Candidate submits practice answer
- **GIVEN** a valid candidate token and an active practice question
- **WHEN** the candidate submits a practice answer
- **THEN** the system persists one immutable practice result
- **AND** the response returns correctness, the normalized correct answer, analysis, and option comparison

#### Scenario: Candidate changes an already submitted practice answer
- **GIVEN** a practice result has already been returned for one submission
- **WHEN** the candidate wants to answer that question again
- **THEN** the system creates a new practice-answer record rather than modifying the prior result

## ADDED Requirements

### Requirement: Four-Hour Candidate Session
Candidate tokens in the formal internal profile MUST expire no later than four hours after issuance and MUST be invalidated by the guarded close-exam operation.

#### Scenario: Candidate token remains within lifetime
- **GIVEN** a valid candidate token issued less than four hours ago and not invalidated by closure
- **WHEN** the candidate calls an authorized candidate API
- **THEN** the token may be accepted subject to the endpoint's other checks

#### Scenario: Candidate token exceeds lifetime or closure boundary
- **WHEN** a candidate token is older than four hours or was signed before the latest close-exam secret rotation
- **THEN** candidate APIs reject it and the frontend clears the local session

### Requirement: No Manual Login Bypass
The system MUST fail closed when SMTP OTP delivery is unavailable and MUST NOT provide a shared code, administrator-issued bypass token, or manual identity override.

#### Scenario: SMTP is unavailable during login
- **WHEN** OTP delivery cannot complete after the existing bounded retry behavior
- **THEN** no candidate token is issued without successful OTP verification
- **AND** the operator follows the documented stop condition rather than bypassing authentication

### Requirement: Single Active Exam Device
Each in-progress attempt MUST have one active attempt-session generation. Attempt read, save, and submit operations MUST require the current opaque attempt-session credential in addition to the candidate token.

#### Scenario: Active device saves answers
- **GIVEN** a candidate token and the current attempt-session credential
- **WHEN** the device reads, saves, or submits its attempt
- **THEN** the operation may proceed subject to normal attempt rules

#### Scenario: Previous device uses a rotated credential
- **GIVEN** the attempt-session generation was changed by takeover
- **WHEN** the previous device attempts to read, save, or submit
- **THEN** the system rejects the stale attempt-session credential with a conflict response

#### Scenario: Candidate takes over on a new device
- **GIVEN** the candidate completed a fresh OTP login and explicitly confirms takeover
- **WHEN** the takeover request succeeds
- **THEN** the system rotates the attempt-session credential and generation
- **AND** preserves the existing attempt, answers, snapshots, and deadline

### Requirement: Wrong-Question Review
The system SHALL provide each authenticated candidate with a wrong-question review derived from their practice history over the shared question bank.

#### Scenario: Candidate reviews incorrect practice
- **WHEN** the candidate opens wrong-question review
- **THEN** the system lists questions with incorrect practice submissions and supports category filtering
- **AND** does not expose another candidate's history

#### Scenario: Candidate later answers correctly
- **GIVEN** an earlier incorrect practice submission exists
- **WHEN** a later practice submission for the same question is correct
- **THEN** the item is shown as mastered in the current review state
- **AND** the earlier incorrect history remains persisted
