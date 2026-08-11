## Purpose

Defines the macOS Docker Desktop host controls required to operate the lightweight internal exam platform as the current selected formal single-host deployment with a 24x7 best-effort boundary, without claiming high availability, server-grade unattended availability, or continuous operator response.

## ADDED Requirements

### Requirement: Protected macOS Formal Host Layout
The formal macOS deployment SHALL keep versioned releases separate from configuration, backups, evidence, diagnostics, and mutable state under one host root owned by the currently signed-in designated host account. Formal configuration files MUST be excluded from release bundles and MUST be readable only by that account; creating a new dedicated macOS OS account is not required.

#### Scenario: Host layout is initialized
- **WHEN** the operator initializes a new macOS formal host root
- **THEN** configuration, release, backup, evidence, diagnostic, and state directories are created
- **AND** the preflight rejects group- or world-readable formal configuration

#### Scenario: Release contents are inspected
- **WHEN** a release bundle is generated or installed
- **THEN** it contains no formal environment file, database data, media data, backup, diagnostic package, evidence bundle, token, OTP, or credential

### Requirement: Thin macOS Host Operations
The system SHALL provide versioned macOS commands for initialization, release installation and image build, start, stop, status, staging, preflight, backup, second-copy synchronization, restore drill, promotion, same-host rollback, cross-host `prepare-cutover`, cross-host `accept-cutover`, cross-host rollback, operator enablement, session closure, and diagnostic export. Host commands MUST delegate application-specific validation and data operations to versioned containers.

#### Scenario: Application operation is invoked on macOS
- **WHEN** a macOS host command performs backup, restore validation, SMTP preflight, session closure evidence, or lifecycle coordination
- **THEN** it invokes the corresponding command from the selected release container
- **AND** it does not require host Python, Node.js, `uv`, or PostgreSQL tools

#### Scenario: Required prerequisite is unavailable
- **WHEN** Docker Desktop, Docker Compose, the selected release, or protected formal configuration is unavailable
- **THEN** the host command fails closed without mutating formal data or printing secret values

### Requirement: Mandatory macOS Formal LaunchAgent
Docker Desktop SHALL be configured to start after the designated host account signs in, Resource Saver MUST be disabled, and formal containers SHALL use restart policies and bounded logs. An installed and enabled project-owned formal bootstrap LaunchAgent MUST restore the selected formal Compose project after Docker becomes ready; it MUST use bounded retry/backoff and an execution lock, and host or service recovery MUST NOT authorize an exam automatically.

#### Scenario: Formal LaunchAgent is loaded on the real Mac
- **WHEN** the operator installs the accepted formal host configuration
- **THEN** the real `launchctl` load (`bootstrap`) succeeds for the designated account and status (`print`) reports the expected project label, executable path, and bounded log destinations
- **AND** the formal readiness evidence records the loaded status rather than only validating a plist file statically

#### Scenario: Docker readiness retry is exercised
- **GIVEN** Docker Desktop is unavailable when the formal LaunchAgent runs
- **WHEN** the bounded retry schedule is exercised on the real Mac
- **THEN** the LaunchAgent records a retry/failure status and later restores the selected release after Docker becomes ready without building, promoting, or approving an exam

#### Scenario: LaunchAgent lock prevents duplicate recovery
- **GIVEN** one LaunchAgent invocation holds the formal recovery lock
- **WHEN** a second scheduled or retry invocation starts
- **THEN** it exits as a recorded lock skip and does not issue a duplicate Compose recovery

#### Scenario: Designated account signs in after a host restart
- **WHEN** Docker Desktop becomes ready and the bootstrap operation runs for the designated account
- **THEN** the selected formal release is restored without rebuilding or promoting a new version
- **AND** the operator must complete formal preflight before opening an exam

#### Scenario: No designated account has signed in
- **WHEN** macOS has booted but the designated host account session and Docker Desktop are unavailable
- **THEN** the deployment is not described as ready or highly available
- **AND** a scheduled exam may be paused or rescheduled

### Requirement: macOS Formal Preflight
The macOS preflight MUST verify release checksums, architecture, Docker and Compose readiness, explicitly disabled Resource Saver, explicit formal project identity, protected configuration, AC-power and sleep policy, time evidence, FileVault/firewall evidence, fixed private bind address and exact CORS, approved LAN CIDR, loaded `pf` or approved managed-firewall evidence (including the effective rule/status export, such as `pfctl -s info` and `pfctl -sr`), split ingress, disk reserve, migration, service and worker health, real SMTP, verified backup, independent encrypted second-copy evidence on a distinct physical device or host, and browser evidence. Its port gate MUST allow only candidate TCP `8080` from the approved CIDR to the fixed private IP, keep operator `8081`, PostgreSQL `5432`, and direct frontend `5173` loopback-only, leave backend `8000` and the worker unexposed, reject `8080` from an unapproved CIDR, and prove from a second device that `8081`/`5432`/`5173`/`8000` and admin/docs/OpenAPI routes are not reachable.

#### Scenario: Every required macOS check passes
- **WHEN** all required host, release, network, service, SMTP, backup, and browser checks pass
- **THEN** the preflight writes a non-secret checksummed passing evidence record

#### Scenario: A required macOS check fails
- **WHEN** any required preflight check is missing, stale, unsafe, or failed
- **THEN** the preflight writes a failed non-secret evidence record
- **AND** the release or exam MUST NOT be approved

### Requirement: Selected macOS Host Availability Boundary
The selected macOS formal deployment SHALL be described as a single-host 24x7 best-effort service only. It MUST NOT be described as highly available, automatically failover-capable, unattended, or continuously operator-staffed. If the designated account is not signed in or a serious host, disk, power, Docker, or office-network failure occurs, the deployment MUST fail readiness and the exam MAY be paused or rescheduled; no second host or parallel formal writer may be introduced as an unverified remedy.

#### Scenario: Serious host failure occurs
- **WHEN** the Mac, Docker Desktop, disk, power, or office network cannot be recovered within the accepted operating boundary
- **THEN** readiness remains failed and the formal exam is paused or rescheduled
- **AND** no automatic failover or second formal writer is opened

### Requirement: Independent Encrypted Second-Copy Gate
Formal pre-exam, post-exam, pre-upgrade, and cutover backups SHALL include a verified copy in independently encrypted storage on a distinct physical device or host. If the second storage is unavailable, unencrypted, not physically independent, or unverified, each of those formal operations MUST fail closed and MUST NOT produce formal acceptance evidence. Daily opportunistic backup MAY record skipped or degraded status without being treated as a valid formal backup gate.

#### Scenario: Formal second copy is unavailable
- **WHEN** a formal backup or cutover operation cannot verify the independent encrypted second copy
- **THEN** the operation fails closed and formal readiness or cutover is not approved

#### Scenario: Daily opportunity backup is blocked
- **WHEN** a daily opportunistic backup finds an in-progress attempt, lock conflict, unchanged data, or unavailable second storage
- **THEN** it records skipped/degraded status without interrupting exam traffic or claiming formal backup success

### Requirement: macOS Staging Promotion And Rollback
Every macOS release MUST run in a disposable same-host staging project with separate loopback ports and volumes before formal promotion. Promotion SHALL use the already tested architecture-specific images. Same-host version rollback SHALL select the previous release and verified pre-upgrade paired backup plus its independent encrypted second copy, and require explicit typed confirmation when restoring it can discard post-backup writes. Cross-host cutover SHALL use `prepare-cutover` and `accept-cutover`; formal cutover backup and second-copy verification are fail-closed gates; after target writes, cross-host rollback MUST first create and verify the latest target paired backup and independent encrypted second copy, stop the entire target project, and only then restore it to an approved host.

#### Scenario: Staging succeeds
- **WHEN** migration, health, route isolation, browser E2E, SMTP, backup, security, and capacity gates pass in the disposable project
- **THEN** the tested image references and checksummed staging evidence become eligible for formal promotion

#### Scenario: Staging or promotion fails
- **WHEN** a required staging or promotion gate fails
- **THEN** the formal project remains on the last accepted release
- **AND** disposable resources are cleaned without deleting formal volumes

#### Scenario: Same-host rollback follows formal writes
- **WHEN** the new release performed a migration or accepted formal writes before rollback on the same host
- **THEN** the operator must use the verified pre-upgrade paired backup and previous release
- **AND** the operator must confirm the expected loss of writes made after that backup before restoring it
- **AND** application database downgrade is not treated as the standard recovery path

#### Scenario: Cross-host rollback follows target writes
- **WHEN** a target host accepted formal writes and cross-host rollback is required
- **THEN** the target first creates and verifies its latest paired backup, then stops the entire target formal project
- **AND** the newest target backup is restored to the source or another approved host; stale source data is not reopened

### Requirement: macOS Cutover Commands Fence The Whole Project
`prepare-cutover` MUST stop the complete source formal Compose project and write a checksummed manifest containing `datasetId`, source/target `hostId`, previous/next `writerGeneration`, release/image identity, paired-backup checksums, and whole-project stop evidence. `accept-cutover` MUST reject a stale or consumed manifest, missing target restore/preflight, or any running source service before exposing the target candidate gateway.

#### Scenario: Candidate-only shutdown is attempted
- **GIVEN** the source candidate gateway is stopped but backend, worker, database, frontend, or operator gateway remains running
- **WHEN** `accept-cutover` is requested
- **THEN** the operation fails closed and target write traffic is not exposed

#### Scenario: Valid cutover is accepted
- **GIVEN** a valid unconsumed manifest, verified paired backup, isolated target restore, target preflight, and proof that every source formal service is stopped
- **WHEN** `accept-cutover` records the next writer generation
- **THEN** the target becomes the only approved writer for that dataset

### Requirement: macOS Diagnostics And Scheduled Operations
The macOS host SHALL export bounded, redacted, checksummed diagnostics and MAY schedule non-destructive startup/status and opportunistic backup checks. Scheduled operations MUST NOT promote releases, delete data, restore formal data, rotate sessions, or bypass exam-time write gates.

#### Scenario: Diagnostic package is exported
- **WHEN** the operator requests diagnostics
- **THEN** the package records selected version, project state, service and worker health, disk, backup, lock, and bounded logs
- **AND** it excludes formal configuration values, credentials, tokens, OTPs, uploaded content, and unrestricted personal data

#### Scenario: Opportunistic backup check runs during an exam
- **WHEN** a scheduled backup check finds an in-progress formal attempt or cannot obtain the operational lock
- **THEN** it records a skipped result
- **AND** it does not interrupt answer save or submit traffic
