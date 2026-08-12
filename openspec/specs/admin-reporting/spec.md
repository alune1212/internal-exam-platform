# Admin Reporting Specification

## Purpose

Admin reporting covers score, accuracy, wrong-question, absent-candidate, ranking, and Excel export behavior.
## Requirements
### Requirement: Exam-Filterable Reports
The system SHALL support `exam_id` filtering for score, question accuracy, wrong-question, absent-candidate, and export reports. Formal report rows SHALL identify an exam-scoped participant from the frozen roster snapshot (including roster name and normalized roster email, plus any optional exam-scoped organization fields) and MUST NOT read `employee_no`, `phone_suffix`, or global `should_attend` fields. Existing report scope and aggregation semantics SHALL remain unchanged.

#### Scenario: Administrator filters reports by exam
- **GIVEN** submitted attempts exist for multiple exams
- **WHEN** an administrator requests a report with `exam_id`
- **THEN** the response includes data for only that exam
- **AND** each formal participant row uses that exam's frozen roster identity

#### Scenario: Administrator omits exam filter
- **GIVEN** report data exists across exams
- **WHEN** an administrator requests a report without `exam_id`
- **THEN** the response preserves the global report view
- **AND** each formal participant remains associated with the roster identity frozen for its own exam

### Requirement: Attendance Status Uses Latest Attempt State
The system SHALL classify absent-candidate report status from the latest formal attempt state for each scoped participant within the report scope so a participant is not returned in multiple attendance statuses for the same exam. Normal attendance aggregates MUST exclude voided attempts, while retaining the existing latest-attempt and retake semantics. Participant identity in every status row SHALL come from the frozen per-exam roster snapshot and MUST NOT use `employee_no`, `phone_suffix`, or global `should_attend`.

#### Scenario: Candidate has in-progress retake after submitted attempt
- **GIVEN** a candidate has a submitted attempt for an exam
- **AND** the candidate has an unused retake grant that has been consumed by a new in-progress retake attempt
- **WHEN** an administrator requests the in-progress attendance report for that exam
- **THEN** the response includes the candidate as in progress
- **AND** when the administrator requests the submitted attendance report for that exam, the response does not include the candidate
- **AND** the row uses the frozen roster name and email for that exam

#### Scenario: Candidate latest attempt is submitted
- **GIVEN** a candidate has one or more attempts for an exam
- **AND** the latest attempt for that exam is submitted or auto-submitted
- **WHEN** an administrator requests the submitted attendance report for that exam
- **THEN** the response includes the candidate as submitted
- **AND** the candidate is not returned as in progress or not started for that exam

#### Scenario: Candidate has no attempt
- **GIVEN** a scoped participant has no attempt for an exam, regardless of whether the linked account is pending, active, or inactive
- **WHEN** an administrator requests the not-started attendance report for that exam
- **THEN** the response includes the candidate as not started
- **AND** the row uses the frozen roster identity rather than current account status or profile fields

#### Scenario: Latest attempt is voided
- **GIVEN** a scoped participant has only voided attempts for an exam
- **WHEN** an administrator requests a normal attendance report for that exam
- **THEN** the voided attempt does not count as a valid submitted or completed result
- **AND** the participant remains classified according to the non-voided/latest-attempt attendance rules

### Requirement: Report Export Workbook
The system SHALL export reports as a single Excel workbook with separate sheets for score report, question accuracy, wrong questions, and absent candidates. Formal participant columns SHALL use frozen per-exam roster identity and MUST omit `employee_no`, `phone_suffix`, and `should_attend`. Existing filtering, aggregation, workbook structure, and formula-character escaping behavior SHALL be preserved.

#### Scenario: Administrator exports reports
- **GIVEN** report data is available for the selected scope
- **WHEN** the administrator requests report export
- **THEN** the system returns one Excel workbook containing the report sheets
- **AND** formal participant rows use the selected exam's frozen roster identity

#### Scenario: Exported cell begins with formula character
- **GIVEN** exported report text begins with a formula-like character
- **WHEN** the system writes the Excel workbook
- **THEN** the cell value is escaped before export

#### Scenario: Exported identity omits removed fields
- **GIVEN** an exported row represents a formal participant
- **WHEN** the workbook is generated
- **THEN** the identity columns contain the frozen roster name and normalized roster email, with optional exam-scoped organization fields when present
- **AND** no sheet, header, formula, or cell contains `employee_no`, `phone_suffix`, or `should_attend`

### Requirement: Ranking Uses Submitted Results
The system SHALL calculate administrator-only rankings from submitted or auto-submitted formal attempt results, MUST exclude voided attempts, and SHALL identify ranked participants from frozen per-exam roster snapshots. Candidate-facing APIs and pages MUST NOT expose ranking.

#### Scenario: Candidate has submitted attempts
- **GIVEN** candidates have submitted or auto-submitted attempts for an exam
- **WHEN** the ranking endpoint is requested
- **THEN** the ranking reflects persisted eligible attempt scores for that exam
- **AND** the ranking rows use frozen roster identity rather than account or legacy personnel fields

#### Scenario: Administrator requests ranking
- **GIVEN** candidates have submitted or auto-submitted attempts for an exam
- **WHEN** an authenticated operator requests ranking through the loopback admin surface
- **THEN** the ranking reflects persisted eligible attempt scores for that exam
- **AND** excludes voided attempts

#### Scenario: Candidate requests ranking
- **WHEN** a candidate or unauthenticated LAN client requests ranking
- **THEN** the system rejects the request or omits candidate-ranking behavior

### Requirement: Report Export Copy Consistency
The system SHALL use the same product terminology in administrator-facing report workbook sheet names, column headers, and exported status labels as the admin report UI. Identity labels SHALL describe frozen per-exam roster fields and MUST NOT expose `employee_no`, `phone_suffix`, or `should_attend` as headers or status/filter terms.

#### Scenario: Administrator exports report workbook
- **GIVEN** report data is available for the selected scope
- **WHEN** an administrator downloads the report export workbook
- **THEN** the workbook sheet names use the canonical report labels `个人成绩`, `题目正确率`, `错题排行`, and `参考状态`
- **AND** report column headers use synchronized compact bilingual labels for equivalent fields
- **AND** submitted attendance status is exported as `已交卷` rather than an inconsistent submit label or raw API code
- **AND** participant identity headers refer to the frozen roster name and email

#### Scenario: Report export behavior is preserved
- **GIVEN** report export copy changes are applied
- **WHEN** the administrator requests report export with or without `exam_id`
- **THEN** the system preserves the existing report query scope, workbook structure, and Excel cell escaping behavior
- **AND** the export continues to exclude voided attempts from normal aggregates

### Requirement: Frozen Per-Exam Roster Identity in Reports
Every formal report and report export SHALL use the roster identity captured when the exam roster is published: normalized roster email and roster name, plus optional department, position, exam group, and roster remark. A later platform-account display-name change MUST NOT rewrite published roster values or historical formal reports. Report queries and exports MUST never depend on `employee_no`, `phone_suffix`, or global `should_attend`.

#### Scenario: Account profile changes after roster publication
- **GIVEN** a participant's platform display name changes after an exam roster is published
- **WHEN** an administrator opens or exports a report for that exam
- **THEN** the participant is shown with the frozen roster name and normalized roster email
- **AND** published organization fields remain those captured for that exam

#### Scenario: Legacy identity fields are unavailable
- **GIVEN** the migration has removed `employee_no`, `phone_suffix`, and global `should_attend` from the report data contract
- **WHEN** an administrator requests any score, accuracy, wrong-question, attendance, ranking, or export report
- **THEN** the query and response succeed using frozen per-exam roster identity and attempt/scope state
- **AND** no response, workbook sheet, header, filter, or aggregate reads or emits those legacy fields
