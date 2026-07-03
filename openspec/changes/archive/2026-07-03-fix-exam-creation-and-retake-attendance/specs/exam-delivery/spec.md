## MODIFIED Requirements

### Requirement: Publish Freezes Exam Question Pool
The system SHALL freeze the current active question bank into exam_question_pool when an existing draft exam becomes active, and SHALL reject direct active exam creation before persistence.

#### Scenario: Exam is published
- **GIVEN** a draft exam and active questions in the question bank
- **WHEN** an administrator publishes the exam
- **THEN** the system stores the frozen question pool for that exam

#### Scenario: Active exam cannot be created directly
- **GIVEN** an administrator creates an exam with active status
- **WHEN** the create request is processed
- **THEN** the system rejects the request
- **AND** the system does not persist an active exam missing a frozen question pool

#### Scenario: Question bank changes after publish
- **GIVEN** an exam has already been published
- **WHEN** questions are later edited, deactivated, or added
- **THEN** new attempts for that exam continue to draw from the frozen exam_question_pool
