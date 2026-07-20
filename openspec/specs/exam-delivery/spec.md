# Exam Delivery Specification

## Purpose

Exam delivery covers exam publishing, fixed-paper generation, attempt snapshots, answer persistence, submit behavior, auto-submit, and retake grants.

## Requirements

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

### Requirement: Fixed-Paper Rule Semantics
The system MUST preserve fixed-paper question_rule semantics for non-empty rules and legacy all-active behavior for empty rules.

#### Scenario: Fixed-paper rule is valid
- **GIVEN** a non-empty question_rule with positive question_count, positive total_score, and type_counts summing to question_count
- **WHEN** a candidate starts the exam
- **THEN** the system selects active unique stems from the frozen pool according to the rule and distributes integer scores from total_score

#### Scenario: Legacy empty rule is used
- **GIVEN** exam.question_rule is an empty object
- **WHEN** a candidate starts the exam
- **THEN** the system uses the legacy all-active frozen-pool behavior

### Requirement: Attempt Snapshots
The system SHALL persist question, option, correct answer, analysis, score, and order snapshots for every formal attempt.

#### Scenario: Candidate starts an exam
- **GIVEN** a candidate is eligible to start an exam
- **WHEN** the system creates the attempt
- **THEN** it persists attempt question snapshots before returning the paper

#### Scenario: Original question changes after attempt start
- **GIVEN** an attempt already has persisted snapshots
- **WHEN** the original question or options change later
- **THEN** scoring and result review continue to use the persisted attempt snapshots

### Requirement: Answer Save And Submit
The system SHALL save answers during an in-progress attempt and SHALL score submitted attempts from snapshot data.

#### Scenario: Candidate saves an answer
- **GIVEN** an in-progress attempt
- **WHEN** the candidate saves an answer
- **THEN** the system persists the current answer without pausing the countdown

#### Scenario: Candidate submits attempt
- **GIVEN** an in-progress attempt with saved or submitted answers
- **WHEN** the candidate submits the attempt manually
- **THEN** the system scores answers against snapshot correct answers and records pass status from the exam rule

### Requirement: Auto-Submit And Retake
The system SHALL support time-based auto-submit and one-use retake grants.

#### Scenario: Attempt reaches time limit
- **GIVEN** an in-progress attempt whose allowed duration has elapsed
- **WHEN** the background auto-submit check runs
- **THEN** the system submits the attempt with submit_type auto

#### Scenario: Candidate starts authorized retake
- **GIVEN** a submitted candidate has an unused retake grant for the exam
- **WHEN** the candidate starts the exam again
- **THEN** the system creates a retake attempt and consumes the grant

### Requirement: Observable Auto-Submit Recovery
The system MUST make auto-submit worker health observable and SHALL safely catch up overdue in-progress attempts after a worker interruption without resubmitting completed attempts.

#### Scenario: Worker completes a successful scan
- **GIVEN** the auto-submit worker can query the database
- **WHEN** it completes a due-attempt scan, whether or not any attempt is due
- **THEN** it refreshes its health heartbeat

#### Scenario: Worker database scans fail
- **GIVEN** repeated worker scans cannot complete because the database is unavailable
- **WHEN** the last successful heartbeat exceeds the configured health age
- **THEN** the worker healthcheck reports unhealthy

#### Scenario: Worker recovers after interruption
- **GIVEN** one or more in-progress attempts became overdue while the worker was unavailable
- **WHEN** a recovered worker completes its next scan
- **THEN** it auto-submits the overdue in-progress attempts using existing snapshot scoring and auto submit type

#### Scenario: Completed attempt is encountered during recovery
- **GIVEN** an attempt was manually submitted or processed by another worker before recovery processing reaches it
- **WHEN** the recovered worker evaluates that attempt
- **THEN** it does not submit or score the completed attempt again
