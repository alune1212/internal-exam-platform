## ADDED Requirements

### Requirement: Future Windows Runtime
The future Windows formal instance SHALL run as a Docker Desktop deployment with the WSL2 backend on a dedicated Windows host, while the selected macOS formal source/target and development data remain unchanged until a deliberate cutover. Real Mac acceptance and future Windows acceptance are separate host-specific gates; neither host may be called ready without its own evidence. The Windows host MUST require only Docker Desktop and PowerShell for documented host operations.

#### Scenario: Operator installs a formal release
- **GIVEN** a dedicated Windows host with Docker Desktop and PowerShell
- **WHEN** the operator installs and starts a supported release bundle
- **THEN** no host installation of Git, Python, `uv`, Node.js, or Bash is required
- **AND** application-specific operations run through versioned containers and PowerShell entrypoints

#### Scenario: Developer changes the Mac environment
- **GIVEN** the Mac development instance and Windows formal instance exist
- **WHEN** development data, containers, or source files change on the Mac
- **THEN** the Windows formal database, media, configuration, and release remain unchanged until an accepted release is promoted

### Requirement: Versioned Release Bundle
Each formal release MUST be delivered as a checksummed bundle tied to one Git commit and MUST pin base container images by digest. Runtime secrets, formal data, backups, diagnostics, and evidence MUST remain outside the version directory.

#### Scenario: Release bundle is inspected
- **WHEN** an operator or release check inspects a bundle
- **THEN** the bundle identifies its Git commit, application version, image digests, included files, and checksums
- **AND** it contains no formal `.env` file, credential, token secret, SMTP password, or production data

#### Scenario: Bundle checksum fails
- **GIVEN** a release bundle file does not match its manifest checksum
- **WHEN** installation or promotion is attempted
- **THEN** the operation fails before changing the formal project

### Requirement: Windows Staging And Promotion Gate
The system MUST validate every release in a disposable same-host Windows Compose project with separate ports and volumes before promotion to the formal project. Promotion MUST use the already tested commit-tagged images rather than rebuilding from floating inputs.

#### Scenario: Staging passes
- **GIVEN** a release was built and tagged for one commit
- **WHEN** the disposable Windows project passes migration, health, browser E2E, SMTP, backup, and capacity checks
- **THEN** the same tested images are eligible for formal promotion

#### Scenario: Staging fails
- **GIVEN** any required disposable-project check fails
- **WHEN** release readiness is assessed
- **THEN** the formal project remains unchanged
- **AND** the disposable project can be removed without touching formal volumes

### Requirement: Split Candidate And Operator Gateways
The deployment SHALL expose a candidate gateway on the configured private LAN address and port `8080` only to the approved private CIDR and a separate operator gateway on `127.0.0.1:8081`. The formal acceptance gate MUST include second-device and unapproved-CIDR negative tests.

#### Scenario: LAN candidate opens the platform
- **WHEN** a LAN client uses the candidate gateway
- **THEN** candidate login, exam, practice, learning, and published media routes are available
- **AND** `/admin`, `/api/admin/*`, operational routes, readiness details, `/docs`, and `/openapi.json` are rejected

#### Scenario: Operator uses the local gateway
- **GIVEN** the operator is using the Windows host locally
- **WHEN** the operator opens `http://127.0.0.1:8081`
- **THEN** authenticated admin and operations routes are available

#### Scenario: LAN client targets internal services
- **WHEN** a LAN client attempts to reach PostgreSQL, the backend port, the direct frontend port, or the worker
- **THEN** those services are not published to the LAN

#### Scenario: Approved-CIDR port gate is exercised
- **GIVEN** the future Windows host has an approved private CIDR and fixed bind address
- **WHEN** a client from the approved CIDR and a client outside that CIDR test the published ports
- **THEN** only candidate `8080` from the approved CIDR is reachable
- **AND** `8081`, `5432`, `5173`, backend `8000`, admin/docs/OpenAPI routes, and worker remain unreachable from the second device or unapproved CIDR

### Requirement: Hard Preflight And Formal Evidence
The Windows release and exam-day workflow MUST fail closed when a required preflight gate fails and MUST write a non-secret checksummed evidence result.

#### Scenario: Formal preflight succeeds
- **GIVEN** the version and configuration are accepted, services are healthy, time and disk checks pass, real SMTP succeeds, the latest required backup is valid, and the browser smoke passes
- **WHEN** preflight completes
- **THEN** it returns success and records the release, checks, timestamps, and artifact identifiers without secret values

#### Scenario: Required preflight fails
- **GIVEN** a required configuration, health, time, disk, SMTP, backup, browser, or migration check fails
- **WHEN** preflight runs
- **THEN** it exits unsuccessfully
- **AND** the release or formal exam MUST NOT be marked ready

### Requirement: Host Recovery And Exam-Safe Updates
Formal Compose services MUST use bounded log rotation and `restart: unless-stopped`. Docker Desktop SHALL start after the dedicated operator signs in, but recovered services MUST pass manual preflight before a formal exam proceeds.

#### Scenario: Windows or Docker restarts
- **WHEN** Docker Desktop becomes available after a host or daemon restart
- **THEN** services configured for automatic recovery restart
- **AND** the operator must confirm preflight before opening or resuming formal operations

#### Scenario: Formal exam freeze period begins
- **GIVEN** a formal exam is scheduled within seven days
- **WHEN** routine application, image, Docker Desktop, or Windows changes are considered
- **THEN** they are deferred unless they fix an evidenced exam-blocking defect
- **AND** automatic sleep, hibernation, or restart is not allowed during the exam window

### Requirement: Local Operations And Diagnostics
The loopback-only operator surface SHALL show the deployed version, migration head, service and worker health, operational lock, disk reserve, recent backup/second-copy/restore state, retention actions, and security-scan state. A PowerShell command MUST export a bounded, redacted diagnostic package.

#### Scenario: Operator inspects service state
- **WHEN** an authenticated operator opens the local operations page
- **THEN** the page distinguishes healthy, degraded, stale, skipped, and failed operational signals
- **AND** it does not expose passwords, tokens, OTPs, or full sensitive configuration

#### Scenario: Operator exports diagnostics
- **WHEN** the local diagnostic command runs
- **THEN** it exports version, non-sensitive configuration facts, health results, bounded logs, and timestamps with a manifest
- **AND** it excludes credentials, bearer tokens, OTPs, and unrestricted request bodies

### Requirement: Capacity And Support Boundary
The formal release SHALL support at most 50 concurrent candidates and MUST pass a 100-client test covering start, answer save, and submit before Windows promotion. Learning and practice MAY run 24×7 on a best-effort basis, while formal exam windows require operator coverage.

#### Scenario: Capacity gate runs
- **WHEN** the release is tested with 100 representative simulated clients
- **THEN** start, save, submit, database connection, and worker-health acceptance thresholds pass before promotion

#### Scenario: Non-exam outage occurs
- **GIVEN** no formal exam is in progress
- **WHEN** the 24×7 learning or practice service fails outside staffed hours
- **THEN** recovery may wait until the next business day without violating the formal exam service boundary

### Requirement: Backup-Based Same-Host Rollback
The standard same-host version rollback MUST use the prior accepted release and the verified paired pre-upgrade backup when a migration or new formal write has occurred. If restoring the backup may discard writes made after it was taken, the operator MUST provide an explicit typed data-loss confirmation and the evidence MUST record that expected loss. A generic Alembic downgrade MUST NOT be the default rollback path.

#### Scenario: Upgrade fails after migration
- **GIVEN** a verified pre-upgrade paired backup and prior release exist
- **WHEN** the promoted release fails after schema migration or formal writes
- **THEN** the operator follows the guarded restore procedure for the paired backup
- **AND** restarts the prior release against the restored database and media state

#### Scenario: Upgrade fails before migration or formal writes
- **WHEN** failure is proven to have occurred before schema or formal-data change
- **THEN** the prior release may be restarted without restoring data

### Requirement: Future Mac-To-Windows Cutover Acceptance
The future Windows acceptance track MUST consume a checksummed `prepare-cutover` manifest containing `datasetId`, source/target `hostId`, previous/next `writerGeneration`, release/image identity, paired-backup checksums, and proof that the entire Mac formal project is stopped. `accept-cutover` MUST not expose the Windows candidate gateway until native Linux AMD64 staging, isolated restore, host/network/security/service recovery, SMTP, browser, capacity, and target preflight gates pass.

#### Scenario: Mac source is only partially stopped
- **GIVEN** the Mac candidate gateway is stopped but another Mac formal service remains running
- **WHEN** Windows `accept-cutover` is requested
- **THEN** Windows acceptance fails closed and no Windows candidate writes are exposed

#### Scenario: Windows target accepts no writes
- **GIVEN** native AMD64 Windows staging and target preflight pass but formal promotion fails before a write
- **WHEN** cross-host rollback is requested
- **THEN** the entire Windows formal project is stopped and the unchanged Mac source may reopen only after manifest reconciliation and preflight

#### Scenario: Windows target accepted writes
- **GIVEN** the Windows target accepted formal writes
- **WHEN** cross-host rollback is requested
- **THEN** Windows first creates and verifies its latest paired backup, stops the entire Windows formal project, and restores that newest backup to the Mac source or another approved host
- **AND** stale Mac data MUST NOT simply be reopened

### Requirement: Scheduled Security Maintenance
The project MUST scan Python dependencies, npm dependencies, and final images at least weekly without automatically deploying updates. Confirmed critical or exploitable high-severity findings MUST block a new release.

#### Scenario: Scheduled scan finds a blocking issue
- **WHEN** the weekly scan confirms a critical or exploitable high-severity issue in the released dependency or image set
- **THEN** the finding is recorded for remediation
- **AND** a new formal release cannot be accepted until the issue is mitigated or explicitly dispositioned

#### Scenario: Routine maintenance has no blocking issue
- **WHEN** no urgent issue requires an out-of-cycle release
- **THEN** dependency and image updates are grouped into the quarterly maintenance release and pass the full release gate
