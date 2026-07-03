## ADDED Requirements

### Requirement: Strict Login Roster Email Validation
The system MUST validate that candidate and exam-candidate import rows provide usable email data for strict candidate email OTP login. Missing, invalid, or conflicting candidate email data MUST be reported as row-level import failures and MUST NOT create exam access that would fail only at candidate login time.

#### Scenario: Candidate import row omits email
- **GIVEN** strict candidate login is enabled for all exams
- **WHEN** an administrator imports a candidate row without a valid email
- **THEN** the system rejects that row with a row-level failure reason
- **AND** the system does not persist that candidate row

#### Scenario: Exam-candidate import creates a new scoped candidate
- **GIVEN** strict candidate login is enabled for all exams
- **WHEN** an administrator imports an exam-candidate row that creates a new candidate
- **THEN** the row MUST include a valid email
- **AND** the persisted candidate MUST store that email before the candidate is scoped to the exam

#### Scenario: Exam-candidate import reuses an existing candidate without email
- **GIVEN** an existing candidate has no usable email
- **WHEN** an administrator imports that candidate into an exam with a valid row email
- **THEN** the system may backfill the candidate email from the row
- **AND** the system may add the candidate to the exam scope

#### Scenario: Exam-candidate import conflicts with existing candidate email
- **GIVEN** an existing candidate already has a usable email
- **WHEN** an administrator imports that candidate into an exam with a different row email
- **THEN** the system rejects that row with a row-level failure reason
- **AND** the system does not change the existing candidate email
