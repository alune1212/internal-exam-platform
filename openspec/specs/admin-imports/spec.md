# Admin Imports Specification

## Purpose

Admin imports cover standardized Excel-based question, candidate, and exam-candidate imports plus failure reports.

## Requirements

### Requirement: Excel-Only Import Path
The system SHALL use standardized Excel templates for first-phase imports and SHALL NOT add Word parsing or queue-based import processing.

#### Scenario: Administrator downloads templates
- **GIVEN** an administrator needs import input files
- **WHEN** the administrator requests question or candidate templates
- **THEN** the system returns Excel templates for the supported import types

#### Scenario: Unsupported document format is requested
- **GIVEN** the first-phase import boundary is in effect
- **WHEN** a change proposes Word parsing for imports
- **THEN** the change is out of scope unless explicitly approved

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
The system SHALL import exam candidates into exam_candidate_scope without deleting global candidate records.

#### Scenario: Existing candidate is imported into an exam
- **GIVEN** a candidate already exists by employee number or by no-employee-number name
- **WHEN** the administrator imports that candidate into an exam list
- **THEN** the system reuses the candidate and adds an exam_candidate_scope record

#### Scenario: Candidate is removed from an exam list
- **GIVEN** a candidate is scoped to an exam
- **WHEN** the administrator removes the candidate from that exam
- **THEN** the system removes only the exam scope record and preserves the global candidate

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

### Requirement: Failure Report Export
The system SHALL provide Excel failure reports for question, candidate, and exam-candidate imports.

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
