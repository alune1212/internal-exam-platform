## MODIFIED Requirements

### Requirement: Controlled LAN Runtime Profile
The system SHALL provide distinct `development`, `internal`, and `production` runtime profiles. The `internal` profile MUST require non-sample credentials, SMTP candidate login delivery, exact private-LAN HTTP origins, an explicit private LAN bind address, an approved private CIDR enforced by the host firewall (`pf` on macOS or the approved Windows equivalent), four-hour formal token lifetimes, and split LAN/loopback entrypoints, while the `production` profile MUST continue requiring HTTPS origins. An `internal` deployment on a shared office LAN MUST be documented as an explicitly accepted first-phase exception and MUST NOT be represented as transport-secure.

#### Scenario: Valid internal profile starts
- **GIVEN** the internal profile has non-sample credentials, SMTP delivery, four-hour token lifetimes, an exact private-LAN HTTP origin, an explicit private bind address, and split entrypoints
- **WHEN** deployment preflight and backend startup validation run
- **THEN** the configuration is accepted for the documented internal HTTP exception

#### Scenario: Unsafe internal profile is rejected
- **GIVEN** the internal profile uses a sample credential, memory email delivery, wildcard or loopback CORS, an omitted, loopback, public, or any-address bind value, an overlong formal token lifetime, or a LAN-exposed admin entry
- **WHEN** deployment preflight or backend startup validation runs
- **THEN** startup is rejected without printing the rejected secret value

#### Scenario: Shared office LAN exception is recorded
- **GIVEN** candidate traffic uses HTTP on the shared office LAN
- **WHEN** formal readiness evidence is generated
- **THEN** it identifies the unencrypted name, email, OTP, token, answer, and result traffic
- **AND** records the local-admin, short-session, route-minimization, and close-exam compensating controls

#### Scenario: Production remains HTTPS only
- **GIVEN** the production profile contains an HTTP origin even when the host is on a private LAN
- **WHEN** backend startup validation runs
- **THEN** startup is rejected

### Requirement: Paired Backup And Isolated Restore Verification
The system SHALL create PostgreSQL and `learning_media` backup artifacts as one checksummed unit and MUST verify restoration only against disposable resources by default. Formal pre/post-exam backups MUST run under an explicit operator-controlled write freeze, while daily backups MAY use the bounded opportunistic write-freeze contract when no formal attempt is in progress.

#### Scenario: Complete paired backup succeeds
- **GIVEN** no formal attempt is in progress and the backup operation owns the write-freeze lock
- **WHEN** the operation successfully captures the database and media volume
- **THEN** it writes a manifest, checksums, and a success marker after both artifacts are complete

#### Scenario: Opportunistic backup cannot run
- **GIVEN** a formal attempt is in progress or the write-freeze lock is unavailable
- **WHEN** the daily backup attempt runs
- **THEN** it records a skipped result without blocking the exam or forcing the lock

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
The system SHALL define a formal internal-release gate that requires automated quality and security checks, healthy services, real SMTP delivery, business UAT, worker recovery, native staging on the selected host, browser E2E, capacity evidence, verified paired-backup restoration, approved-CIDR/port negative tests, and cutover writer evidence when the selected host changes.

#### Scenario: Internal release evidence is complete
- **GIVEN** backend, frontend, OpenSpec, Compose, dependency, image, and selected-host release checks pass
- **AND** backend and worker healthchecks pass
- **AND** real OTP delivery, formal exam UAT, browser E2E, 100-client capacity, worker interruption recovery, isolated restore verification, and approved-CIDR/port negative tests pass
- **WHEN** release readiness is assessed
- **THEN** the selected deployment may be marked ready for formal internal use only if its host-specific evidence identifies the active writer

#### Scenario: Required release evidence is missing
- **GIVEN** any required configuration, healthcheck, security, SMTP, browser, capacity, UAT, worker recovery, staging, or restore evidence is missing or failed
- **WHEN** release readiness is assessed
- **THEN** the deployment MUST NOT be marked ready for formal internal use

### Requirement: Exactly-One-Writer Cutover Evidence
When formal service moves between macOS and Windows, readiness MUST include an unconsumed checksummed cutover manifest with `datasetId`, source/target `hostId`, previous/next `writerGeneration`, paired-backup checksums, and proof that the entire source formal project is stopped. A target MUST NOT be opened for candidate writes from a Mac-only or Windows-only local evidence bundle.

#### Scenario: Source writer is not fully stopped
- **GIVEN** the source candidate gateway is down but any source backend, worker, database, frontend, or operator gateway remains running
- **WHEN** target readiness is assessed
- **THEN** readiness fails closed and no target candidate writes are accepted

#### Scenario: Future Mac-to-Windows target is accepted
- **GIVEN** native Linux AMD64 Windows staging and UAT pass against the restored Mac paired backup
- **AND** the entire Mac formal project is stopped and `accept-cutover` records the next writer generation
- **WHEN** formal readiness is assessed
- **THEN** Windows may become the active writer and the Mac evidence remains source-history evidence only

## ADDED Requirements

### Requirement: HTTP Exception Reassessment Triggers
The accepted internal HTTP exception MUST be reassessed when concurrency exceeds 50, the network boundary expands, remote administration is requested, data sensitivity increases, a suspected interception incident occurs, or trusted DNS, TLS, or network-isolation capability becomes available.

#### Scenario: Exception trigger occurs
- **WHEN** any documented reassessment trigger occurs
- **THEN** the existing HTTP acceptance cannot be reused silently
- **AND** release readiness records a new transport-risk decision before expanded operation

### Requirement: Formal Session Closure Evidence
The formal exam workflow MUST invalidate all issued admin and candidate sessions after the operator confirms that no attempt remains in progress.

#### Scenario: Operator closes a completed exam window
- **GIVEN** no attempt is in progress
- **WHEN** the guarded close-exam operation rotates the signing secret and recreates the backend
- **THEN** previously issued tokens are rejected
- **AND** readiness and non-secret closure evidence are recorded

#### Scenario: Operator attempts closure during an exam
- **GIVEN** one or more attempts are in progress
- **WHEN** close-exam is requested
- **THEN** the operation refuses to rotate the secret or recreate the backend
