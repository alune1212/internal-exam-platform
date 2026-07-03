## ADDED Requirements

### Requirement: Attendance Status Uses Latest Attempt State
The system SHALL classify absent-candidate report status from the latest formal attempt state for each candidate within the report scope so a candidate is not returned in multiple attendance statuses for the same exam.

#### Scenario: Candidate has in-progress retake after submitted attempt
- **GIVEN** a candidate has a submitted attempt for an exam
- **AND** the candidate has an unused retake grant that has been consumed by a new in-progress retake attempt
- **WHEN** an administrator requests the in-progress attendance report for that exam
- **THEN** the response includes the candidate as in progress
- **AND** when the administrator requests the submitted attendance report for that exam, the response does not include the candidate

#### Scenario: Candidate latest attempt is submitted
- **GIVEN** a candidate has one or more attempts for an exam
- **AND** the latest attempt for that exam is submitted or auto-submitted
- **WHEN** an administrator requests the submitted attendance report for that exam
- **THEN** the response includes the candidate as submitted
- **AND** the candidate is not returned as in progress or not started for that exam

#### Scenario: Candidate has no attempt
- **GIVEN** an active scoped candidate has no attempt for an exam
- **WHEN** an administrator requests the not-started attendance report for that exam
- **THEN** the response includes the candidate as not started
