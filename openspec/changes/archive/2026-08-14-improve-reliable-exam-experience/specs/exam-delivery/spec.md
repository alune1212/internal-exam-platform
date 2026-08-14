## ADDED Requirements

### Requirement: Serialized Attempt Start And Archive Transition
The system MUST serialize a candidate's attempt-start decision with an administrator's transition of the same exam from active to archived. Once the archive transition commits, no new attempt may be created for that exam, and an exam with any in-progress attempt MUST NOT be archived.

#### Scenario: Archive commits before start reaches the lifecycle decision
- **GIVEN** a candidate has observed an active exam but has not created an attempt
- **WHEN** an administrator archives the exam before the start transaction obtains the shared lifecycle decision
- **THEN** the start operation reloads the exam state and rejects the request
- **AND** no attempt or attempt-question snapshot is created

#### Scenario: Start commits before archive reaches the lifecycle decision
- **WHEN** a valid start transaction obtains the shared lifecycle decision and creates an in-progress attempt before an archive request
- **THEN** the archive operation observes the in-progress attempt and rejects the transition
- **AND** the created attempt remains resumable under the existing snapshot and deadline rules

#### Scenario: Exam has no in-progress attempts
- **GIVEN** an active exam has no in-progress attempt
- **WHEN** an authorized administrator archives it
- **THEN** the transition commits under the existing admin writer gate
- **AND** subsequent start requests are rejected as inactive

#### Scenario: Concurrent starts remain idempotent
- **WHEN** two valid start requests for the same scoped candidate race while the exam remains active
- **THEN** at most one in-progress attempt is stored
- **AND** both successful responses resolve to the same resumable attempt under the existing uniqueness contract

