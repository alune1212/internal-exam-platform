## ADDED Requirements

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
