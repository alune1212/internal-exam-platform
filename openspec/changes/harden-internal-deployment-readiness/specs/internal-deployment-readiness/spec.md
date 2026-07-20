## ADDED Requirements

### Requirement: Controlled LAN Runtime Profile
The system SHALL provide distinct `development`, `internal`, and `production` runtime profiles. The `internal` profile MUST require non-sample credentials, SMTP candidate login delivery, exact private-LAN HTTP origins, and an explicit private LAN bind address, while the `production` profile MUST continue requiring HTTPS origins.

#### Scenario: Valid internal profile starts
- **GIVEN** the internal profile has non-sample credentials, SMTP delivery, an exact private-LAN HTTP origin, and an explicit private bind address
- **WHEN** deployment preflight and backend startup validation run
- **THEN** the configuration is accepted for controlled-LAN operation

#### Scenario: Unsafe internal profile is rejected
- **GIVEN** the internal profile uses a sample credential, memory email delivery, wildcard or loopback CORS, or an omitted, loopback, public, or any-address bind value
- **WHEN** deployment preflight or backend startup validation runs
- **THEN** startup is rejected without printing the rejected secret value

#### Scenario: Production remains HTTPS only
- **GIVEN** the production profile contains an HTTP origin even when the host is on a private LAN
- **WHEN** backend startup validation runs
- **THEN** startup is rejected

### Requirement: Role-Scoped Runtime Configuration
The deployment MUST distinguish backend and worker runtime roles and MUST propagate documented backend settings without exposing unrelated backend secrets to the auto-submit worker.

#### Scenario: Backend receives supported overrides
- **GIVEN** token TTL, rate-limit, OTP, SMTP, import, and media settings are configured in the deployment environment
- **WHEN** Docker Compose renders the backend service
- **THEN** the backend container receives those configured values

#### Scenario: Worker receives only required settings
- **GIVEN** Docker Compose renders the auto-submit worker service
- **WHEN** its environment is inspected by configuration tests
- **THEN** it contains the database and worker runtime settings
- **AND** it does not contain SMTP passwords or administrator credentials

### Requirement: Dependency-Aware Readiness
The system SHALL keep liveness separate from readiness and MUST report the backend ready only when its required database and learning-media dependencies are usable.

#### Scenario: Liveness does not perform dependency checks
- **WHEN** a client requests `/api/health`
- **THEN** the system reports process liveness without requiring a database query or media write check

#### Scenario: Backend dependencies are ready
- **GIVEN** the database responds and the configured learning-media directory has the required access
- **WHEN** a client requests `/api/ready`
- **THEN** the system returns a successful ready response

#### Scenario: Backend dependency is unavailable
- **GIVEN** the database is unavailable or the configured learning-media directory is unusable
- **WHEN** a client requests `/api/ready`
- **THEN** the system returns HTTP 503 with a non-sensitive response

### Requirement: Observable Worker Health
The auto-submit worker MUST expose health based on recent successful database scans rather than process existence alone.

#### Scenario: Successful scan refreshes health
- **GIVEN** the worker successfully completes a due-attempt scan, including a scan with no due attempts
- **WHEN** the worker healthcheck runs within the allowed heartbeat age
- **THEN** the worker is healthy

#### Scenario: Repeated scan failure becomes unhealthy
- **GIVEN** the worker cannot complete database scans for longer than the allowed heartbeat age
- **WHEN** the worker healthcheck runs
- **THEN** the worker is unhealthy

### Requirement: Paired Backup And Isolated Restore Verification
The system SHALL create PostgreSQL and `learning_media` backup artifacts as one checksummed unit and MUST verify restoration only against disposable resources by default.

#### Scenario: Complete paired backup succeeds
- **GIVEN** no formal exam or video upload is in progress during the maintenance window
- **WHEN** the backup operation successfully captures the database and media volume
- **THEN** it writes a manifest, checksums, and a success marker after both artifacts are complete

#### Scenario: Partial backup is not valid
- **GIVEN** either the database dump or media archive fails or has a checksum mismatch
- **WHEN** backup completion is evaluated
- **THEN** no success marker is produced
- **AND** restore verification rejects the backup

#### Scenario: Restore verification is isolated
- **GIVEN** a complete backup is selected for verification
- **WHEN** the restore verification operation runs
- **THEN** it restores into a disposable database and temporary media volume
- **AND** it refuses to target the current formal deployment by default

### Requirement: Internal Release Gate
The system SHALL define a formal internal-release gate that requires automated quality checks, healthy services, real SMTP delivery, business UAT, worker recovery, and verified backup restoration.

#### Scenario: Internal release evidence is complete
- **GIVEN** backend, frontend, OpenSpec, and Compose checks pass
- **AND** backend and worker healthchecks pass
- **AND** real OTP delivery, formal exam UAT, worker interruption recovery, and isolated restore verification pass
- **WHEN** release readiness is assessed
- **THEN** the deployment may be marked ready for formal internal use

#### Scenario: Required release evidence is missing
- **GIVEN** any required healthcheck, SMTP, UAT, worker recovery, or restore verification evidence is missing or failed
- **WHEN** release readiness is assessed
- **THEN** the deployment MUST NOT be marked ready for formal internal use
