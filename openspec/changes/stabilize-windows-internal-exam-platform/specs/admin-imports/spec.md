## ADDED Requirements

### Requirement: Import Write Gate
Question, candidate, and exam-roster import mutations MUST be rejected while a formal attempt is in progress or while the coordinated backup write-freeze lock is active. Existing import template, bounded validation, persistence, and failure-report behavior MUST remain unchanged outside the gate.

#### Scenario: Import is attempted during a formal exam
- **GIVEN** at least one formal attempt is in progress
- **WHEN** an authenticated operator uploads a question, candidate, or exam-roster workbook
- **THEN** the system rejects the import with a stable conflict response
- **AND** it does not create an import batch or partially persist rows

#### Scenario: Import is attempted during backup freeze
- **GIVEN** the backup operation owns the write-freeze lock
- **WHEN** an authenticated operator starts an import
- **THEN** the system rejects the import with a retryable response
- **AND** it does not extend or break the backup lock

#### Scenario: Import is attempted outside protected windows
- **GIVEN** no formal attempt is in progress and no write freeze is active
- **WHEN** an authenticated operator uploads a supported workbook
- **THEN** the existing size, row, sheet, row-validation, persistence, and failure-report contracts apply
