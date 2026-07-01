# Admin Reporting Specification

## Purpose

Admin reporting covers score, accuracy, wrong-question, absent-candidate, ranking, and Excel export behavior.

## Requirements

### Requirement: Exam-Filterable Reports
The system SHALL support exam_id filtering for score, question accuracy, wrong-question, absent-candidate, and export reports.

#### Scenario: Administrator filters reports by exam
- **GIVEN** submitted attempts exist for multiple exams
- **WHEN** an administrator requests a report with exam_id
- **THEN** the response includes data for only that exam

#### Scenario: Administrator omits exam filter
- **GIVEN** report data exists across exams
- **WHEN** an administrator requests a report without exam_id
- **THEN** the response preserves the global report view

### Requirement: Report Export Workbook
The system SHALL export reports as a single Excel workbook with separate sheets for score report, question accuracy, wrong questions, and absent candidates.

#### Scenario: Administrator exports reports
- **GIVEN** report data is available for the selected scope
- **WHEN** the administrator requests report export
- **THEN** the system returns one Excel workbook containing the report sheets

#### Scenario: Exported cell begins with formula character
- **GIVEN** exported report text begins with a formula-like character
- **WHEN** the system writes the Excel workbook
- **THEN** the cell value is escaped before export

### Requirement: Ranking Uses Submitted Results
The system SHALL calculate rankings from submitted or auto-submitted formal attempt results.

#### Scenario: Candidate has submitted attempts
- **GIVEN** candidates have submitted or auto-submitted attempts for an exam
- **WHEN** the ranking endpoint is requested
- **THEN** the ranking reflects persisted attempt scores for that exam
