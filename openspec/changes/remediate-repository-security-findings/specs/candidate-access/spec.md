## MODIFIED Requirements

### Requirement: Practice API Privacy
The system MUST require `X-Candidate-Token` from an active account for practice APIs and MUST use the same shared active question bank that formal exams draw from. Practice question responses MUST omit correct answers and analysis before submission. After an authenticated candidate submits one bounded answer, the response SHALL reveal that submission's correctness, normalized correct answer, analysis, and selected-versus-correct option comparison. Each accepted submission MUST remain immutable, update the account-question all-time aggregate in the same transaction, and be subject to the documented account/source rate limit and hot-history ceiling.

#### Scenario: Candidate lists practice questions
- **GIVEN** a valid candidate token for an active account
- **WHEN** the candidate requests practice questions
- **THEN** the response draws from the shared active question bank
- **AND** it omits correct answers and analysis

#### Scenario: Candidate submits practice answer
- **GIVEN** a valid candidate token, an active practice question, and available hot-history capacity
- **WHEN** the candidate submits an answer within the documented length and rate limits
- **THEN** the system persists one immutable practice result and atomically updates its all-time aggregate
- **AND** the response returns correctness, the normalized correct answer, analysis, and option comparison

#### Scenario: Candidate changes an already submitted practice answer
- **GIVEN** a practice result has already been returned for one submission
- **WHEN** the candidate answers that question again within the documented boundaries
- **THEN** the system creates a new immutable practice-answer record rather than modifying the prior result
- **AND** atomically advances the all-time aggregate to the latest result

#### Scenario: Candidate exceeds a practice boundary
- **WHEN** an answer exceeds the supported length, the submission rate is exceeded, or the account has reached the hot-history ceiling
- **THEN** the system rejects the submission with the documented validation, rate-limit, or conflict response
- **AND** it persists neither a detail row nor a partial aggregate update

### Requirement: Wrong-Question Review
The system SHALL provide each authenticated active account with a paginated wrong-question review derived only from that account's practice aggregates and retained detail over the shared question bank. Review results MUST support the existing category and mastered-state filters, stable latest-activity ordering, bounded recent-history detail, and all-time attempt/error counts without exposing another account's history.

#### Scenario: Candidate reviews incorrect practice
- **GIVEN** an active account has an all-time aggregate with at least one incorrect submission
- **WHEN** the candidate requests a bounded wrong-question page
- **THEN** the system returns only the requested page in stable latest-activity order
- **AND** it returns at most the requested recent-history count with total/truncated metadata
- **AND** it does not expose another account's practice history

#### Scenario: Candidate later answers correctly
- **GIVEN** an earlier incorrect practice submission exists
- **WHEN** a later practice submission for the same question is correct
- **THEN** the aggregate and current review show the item as mastered
- **AND** all-time attempt and error counts do not decrease when old detail is archived

## ADDED Requirements

### Requirement: Guarded Practice Detail Retention
The system MUST keep at most 5000 hot practice-answer detail rows per account and treat details older than 365 days as archive candidates. Archival deletion MUST be an explicit administrator operation that preserves all-time aggregate state and reduces a capacity-blocked account to 4000 hot rows.

#### Scenario: Account reaches hot-history capacity
- **GIVEN** an account has 5000 retained practice-answer detail rows
- **WHEN** it attempts another practice submission
- **THEN** the system returns a stable conflict response until an administrator completes guarded archival deletion

#### Scenario: Archived details are deleted safely
- **GIVEN** an archive exactly binds eligible detail rows and a later paired backup has passed validation
- **WHEN** an administrator confirms deletion against an unchanged preview fingerprint
- **THEN** the system deletes only the archived detail identifiers
- **AND** preserves the account-question aggregate and unarchived hot rows
