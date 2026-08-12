# Admin Imports Specification

## Purpose

Admin imports cover standardized Excel-based question, candidate, and exam-candidate imports plus failure reports.
## Requirements
### Requirement: Excel-Only Import Path

The system SHALL use standardized Excel templates for first-phase question and exam-roster imports and SHALL NOT add Word parsing or queue-based import processing.

#### Scenario: Administrator downloads templates

- **GIVEN** an administrator needs import input files
- **WHEN** the administrator requests a question or exam-roster template
- **THEN** the system returns an Excel template for the supported import type

#### Scenario: Unsupported document format is requested

- **GIVEN** the first-phase import boundary is in effect
- **WHEN** a change proposes Word parsing for imports
- **THEN** the change is out of scope unless explicitly approved

#### Scenario: Legacy standalone candidate template is submitted

- **GIVEN** an administrator has a workbook or endpoint request using the previous standalone candidate-import contract
- **WHEN** it is submitted after this change
- **THEN** the system returns the stable unsupported-import response and directs the administrator to the email-and-roster-name exam template
- **AND** it creates neither a platform account nor an exam scope

### Requirement: Bounded Import Validation
The system MUST enforce upload size, row count, and worksheet count limits before persisting valid import rows.

#### Scenario: Import file exceeds configured limits
- **GIVEN** an import file exceeds the configured upload, row, or worksheet limits
- **WHEN** the administrator submits the import
- **THEN** the system rejects the import with a business error and does not persist imported rows

#### Scenario: Import contains mixed valid and invalid rows
- **GIVEN** an Excel import contains both valid and invalid rows
- **WHEN** the administrator submits the import
- **THEN** the system persists valid rows and records failed rows with reasons in import_batch metadata

### Requirement: Exam Candidate Scope Import

The system SHALL import exam candidates into `exam_candidate_scope` for draft exams without deleting global platform accounts. Scope matching MUST use the normalized, case-insensitive email key rather than employee number or a name-only fallback. An existing active or pending account is reused by that key; a new valid email creates a pending account that is then scoped to the draft exam. An inactive account is a row-level conflict until an administrator reactivates it. Published exam scope imports and mutations MUST be rejected without changing data.

#### Scenario: Existing candidate is imported into an exam

- **GIVEN** an active or pending platform account already exists for the normalized roster email
- **WHEN** the administrator imports that email into a draft exam roster
- **THEN** the system reuses the account and adds or updates one `exam_candidate_scope` record
- **AND** it does not create another account or delete the global account

#### Scenario: New email is imported into an exam

- **GIVEN** no platform account exists for a valid roster email
- **WHEN** the administrator imports that email into a draft exam roster
- **THEN** the system creates a pending account keyed by the normalized email
- **AND** it adds the exam scope without making the pending account candidate-token capable

#### Scenario: Candidate is removed from an exam list

- **GIVEN** a candidate is scoped to a draft exam
- **WHEN** the administrator removes the candidate from that draft exam
- **THEN** the system removes only the exam scope record and preserves the global account

#### Scenario: Published exam roster mutation is requested

- **GIVEN** an exam roster has been frozen by publication
- **WHEN** an administrator imports, adds, updates, or removes a scope row
- **THEN** the system returns a stable conflict response
- **AND** the published scope and platform account remain unchanged

#### Scenario: Inactive account email is imported

- **GIVEN** a completed account for the normalized roster email is `inactive`
- **WHEN** the administrator imports that email into a draft exam roster
- **THEN** the row fails with an account-reactivation reason
- **AND** the system creates neither a duplicate account nor a scope

### Requirement: Strict Login Roster Email Validation

The system MUST validate that exam-roster import rows provide a usable normalized email and roster name for email OTP registration or login. Missing, invalid, duplicate, or conflicting email data MUST be reported as row-level import failures and MUST NOT create exam access that would fail only at account authentication time.

#### Scenario: Candidate import row omits email

- **GIVEN** a legacy standalone candidate-import row omits a usable email
- **WHEN** an administrator submits it after the standalone contract is retired
- **THEN** the system rejects the legacy row and directs the administrator to the exam-roster template
- **AND** the system does not persist an account or exam scope for that row

#### Scenario: Exam-candidate import creates a new scoped candidate

- **GIVEN** strict candidate email authentication is enabled for all exams
- **WHEN** an administrator imports an exam-candidate row that creates a new account
- **THEN** the row MUST include a valid email and roster name
- **AND** the persisted account MUST be keyed by the normalized email before it is scoped to the exam

#### Scenario: Exam-candidate import reuses an existing candidate without email

- **GIVEN** a legacy account has no usable email after migration
- **WHEN** an administrator imports an exam-candidate row with a valid email
- **THEN** the system rejects the row for operator conflict resolution rather than silently merging identities
- **AND** the system does not backfill an email or add the account to the exam scope automatically

#### Scenario: Exam-candidate import conflicts with existing candidate email

- **GIVEN** an existing account already owns a normalized email
- **WHEN** an import row refers to a different email through a legacy or ambiguous identity
- **THEN** the system rejects that row with a row-level failure reason
- **AND** the system does not change the existing account email or create an unintended scope

### Requirement: Failure Report Export

The system SHALL provide Excel failure reports for question and exam-roster imports.

#### Scenario: Import batch has failed rows

- **GIVEN** an import batch has failed rows
- **WHEN** the administrator downloads the failure report
- **THEN** the workbook contains batch metadata and row-level failure reasons

#### Scenario: Import batch has no failed rows

- **GIVEN** an import batch exists with no failed rows
- **WHEN** the administrator downloads the failure report
- **THEN** the system still returns a workbook with an empty failure-detail sheet

### Requirement: Import Export Copy Consistency
The system SHALL use the same product terminology in administrator-facing import templates, failure-report workbooks, and download filenames as the admin import UI.

#### Scenario: Administrator downloads import templates
- **GIVEN** an administrator needs import input files
- **WHEN** the administrator downloads question or roster import templates
- **THEN** the generated workbook sheet names and download filenames use the canonical labels `题库导入模板` and `应考名单导入模板`

#### Scenario: Administrator downloads failure report
- **GIVEN** an import batch exists for question, roster, or exam-roster import
- **WHEN** the administrator downloads the failure report workbook
- **THEN** the workbook uses product-facing import type labels, the canonical filename `失败明细.xlsx`, and failure detail headers `ROW · 行号` and `REASON · 原因`

#### Scenario: Import contracts are preserved
- **GIVEN** import export copy changes are applied
- **WHEN** an import template is parsed or an import result is returned through the API
- **THEN** upload template field keys, import result response fields, and stored `import_batch.error_report` JSON keys remain compatible with existing clients

### Requirement: Exam-Roster Workbook Contract

The exam-roster Excel workbook MUST require `email` and `candidate_name` columns. On persistence, `candidate_name` becomes the frozen scope `roster_name`. `department`, `position`, `exam_group`, and `remark` MAY be supplied as optional organization or roster fields. The workbook, import schemas, persisted scope data, exports, and failure details MUST NOT accept or emit the removed `employee_no`, `phone_suffix`, `should_attend`, or candidate `status` fields; account lifecycle status remains a server-managed pending/active/inactive value outside the workbook contract. Email matching MUST trim and normalize case before lookup and uniqueness checks. Existing configured upload-size, row-count, and worksheet-count limits MUST be enforced before any account or scope row is persisted.

#### Scenario: Valid roster row uses the reduced contract

- **GIVEN** an administrator uploads a row with valid `email` and `candidate_name`
- **AND** any supplied organization fields are within their optional columns
- **WHEN** the row passes the configured import bounds and validation
- **THEN** the system persists the normalized email and frozen-roster source fields without employee, phone, attendance, or imported account-status fields

#### Scenario: Required roster field is missing

- **GIVEN** an exam-roster row omits `email` or `candidate_name`, or provides an unusable email
- **WHEN** the administrator submits the workbook
- **THEN** the system records a row-level failure reason
- **AND** it does not create an account or exam scope for that row

#### Scenario: Deprecated roster fields are supplied

- **GIVEN** a workbook contains `employee_no`, `phone_suffix`, `should_attend`, or `status` columns from the legacy candidate template
- **WHEN** the administrator submits the workbook
- **THEN** the system rejects the legacy contract with a migration-oriented validation error
- **AND** it does not persist those fields or use them for matching

#### Scenario: Optional organization fields are blank

- **GIVEN** a valid row supplies only the required email and candidate name
- **WHEN** the administrator submits the workbook
- **THEN** the system accepts the row with null optional department, position, exam group, and remark values

### Requirement: Import Write Gate

Question and exam-roster import mutations MUST be rejected while a formal attempt is in progress or while the coordinated backup write-freeze lock is active. Existing import template, bounded validation, persistence, and failure-report behavior MUST remain unchanged outside the gate.

#### Scenario: Import is attempted during a formal exam

- **GIVEN** at least one formal attempt is in progress
- **WHEN** an authenticated operator uploads a question or exam-roster workbook
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
