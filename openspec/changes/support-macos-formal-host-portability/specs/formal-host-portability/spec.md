## Purpose

Defines how one checksummed application release and one verified portable data format can move between macOS ARM64 and Windows WSL2 AMD64 hosts without copying runtime internals or allowing concurrent formal writers.

## ADDED Requirements

### Requirement: Architecture-Aware Release Identity
Every formal release SHALL identify the Git commit, application version, host operating system, CPU architecture, migration head, release-file checksums, and architecture-specific final-image references. Evidence from one host architecture MUST NOT be represented as image or host acceptance evidence for another architecture.

#### Scenario: Apple Silicon release is built
- **WHEN** the checksummed release inputs are built on the current macOS ARM64 host
- **THEN** the manifest identifies `darwin` and `arm64` and records the resulting image references and scan evidence
- **AND** it does not claim those local images are directly loadable on an AMD64 Windows host

#### Scenario: Windows migration release is built
- **WHEN** the same checksummed release inputs are later built for Windows Docker Desktop with Linux AMD64 containers
- **THEN** a separate architecture-specific image manifest, staging result, security result, and host acceptance bundle are produced

### Requirement: Portable Formal Data Unit
Formal data SHALL move between hosts only as a verified paired PostgreSQL custom-format dump and learning-media archive with a manifest, SHA-256 checksums, migration head, representative counts, and a success marker written last. Formal pre-exam, post-exam, pre-upgrade, and cutover backups MUST also be synchronized to an independent encrypted second storage on a distinct physical device or host; an unavailable or unverified second copy MUST fail those formal gates closed. Daily opportunistic backup MAY record skipped/degraded status without claiming formal backup success. Raw Docker volumes and Docker Desktop VM disks MUST NOT be accepted as migration artifacts.

#### Scenario: Portable backup is accepted
- **WHEN** both database and media artifacts pass checksum, manifest, migration, count, and sample validation
- **THEN** the paired backup is eligible for second-copy retention and isolated restore on another supported host

#### Scenario: Formal second copy is unavailable
- **WHEN** the configured second storage is unavailable, not physically independent, unencrypted, or cannot be verified
- **THEN** formal pre-exam, post-exam, pre-upgrade, and cutover readiness fails closed
- **AND** a daily opportunistic backup records a skipped/degraded outcome rather than reporting formal backup success

#### Scenario: Raw runtime data is supplied
- **WHEN** an operator supplies `Docker.raw`, a named-volume directory, an incomplete archive, or an artifact without a valid success marker
- **THEN** migration validation rejects the input without modifying the target formal project

### Requirement: Cutover Identity And Writer Fence
Each formal dataset SHALL have an immutable `datasetId`. Each formal host/project SHALL have a unique `hostId`, and each accepted formal writer SHALL use a monotonically increasing `writerGeneration` (the initial writer is generation `1`; every accepted cutover uses exactly `previous + 1`, never a reused or skipped generation). A checksummed cutover manifest MUST bind the dataset, source and target host IDs, previous and next writer generations, release/image identity, paired-backup ID and checksums, quiescence evidence, source-stop evidence, and acceptance timestamps. `prepare-cutover` and `accept-cutover` MUST reject a missing, stale, mismatched, or already-consumed manifest.

#### Scenario: Initial writer generation is commissioned
- **WHEN** a fresh macOS formal root completes its explicit generation-1 `Prepare`/`Activate` commissioning flow
- **THEN** the resulting identity binds one immutable `datasetId`, current `hostId`, and `writerGeneration=1`
- **AND** no cutover manifest is required for this initial writer, while every later host transition MUST use the cutover manifest and generation increment rules above

#### Scenario: Source prepares a cutover
- **WHEN** an operator runs `prepare-cutover` for a selected target host
- **THEN** the operation writes a final verified paired backup and a checksummed manifest with `datasetId`, source/target `hostId`, and the next `writerGeneration`
- **AND** it stops the entire source formal Compose project, including candidate/operator gateways, frontend, backend, worker, and database
- **AND** the manifest records that no source formal service remains running before target acceptance

#### Scenario: Target accepts a cutover
- **GIVEN** a valid unconsumed manifest, isolated target restore, target preflight, and proof that the entire source formal project is stopped
- **WHEN** the operator runs `accept-cutover`
- **THEN** the target records the next `writerGeneration` and becomes the only candidate-writable formal project for that `datasetId`
- **AND** a source or target with an older generation is rejected from reopening as a writer

### Requirement: Exactly One Active Formal Writer
At most one macOS or Windows formal project SHALL expose candidate write traffic for a given `datasetId` at a time. Host migration MUST prove that the source is quiescent and that its entire formal project is stopped before the target formal project is opened; stopping only a candidate gateway is insufficient.

#### Scenario: Host cutover begins
- **WHEN** the operator prepares to move formal service from macOS to Windows or back
- **THEN** the system requires no in-progress attempt, a verified final paired backup, a `prepare-cutover` manifest, whole-source-project shutdown, and target restore/preflight before target exposure

#### Scenario: Two hosts would be active
- **WHEN** source and target candidate gateways or writable projects would operate concurrently against divergent data
- **THEN** cutover is blocked and the condition is recorded as failed evidence

### Requirement: Cross-Host Cutover And Rollback
The target host MUST restore the final source backup into disposable resources and pass migration, counts, media, SMTP, split-route, browser, security, capacity, and service-recovery gates before formal cutover. Rollback rules SHALL distinguish whether the target accepted writes.

#### Scenario: Target has accepted no writes
- **WHEN** target promotion fails before any formal write is accepted
- **THEN** the entire target formal project is stopped and the unchanged source release may be reopened only after its readiness check and writer-manifest reconciliation

#### Scenario: Target has accepted writes
- **WHEN** rollback is required after the target accepted formal data changes
- **THEN** a new verified paired backup of the latest target data is created before the target project is stopped
- **AND** the entire target formal project is stopped before that backup is restored to the source or another approved host
- **AND** the stale source data MUST NOT simply be reopened

### Requirement: Same-Host Version Rollback
A same-host release rollback SHALL select the previous accepted release and its verified pre-upgrade paired backup. If restoring that backup can discard formal writes made after the backup, the operation MUST require an explicit typed data-loss confirmation and record the expected loss in non-secret evidence; a generic database downgrade or silent restore is not acceptable.

#### Scenario: Same-host rollback would discard writes
- **GIVEN** the new release migrated or accepted formal writes after the pre-upgrade backup
- **WHEN** the operator requests same-host rollback
- **THEN** the previous release and pre-upgrade paired backup are selected
- **AND** rollback refuses to restore until the operator enters the exact data-loss confirmation
- **AND** the evidence records that post-backup writes may be lost

### Requirement: Host-Specific Acceptance Evidence
Automated application checks MAY be reused across platforms, but Docker Desktop startup, host power/time/security, networking, native image build, restart recovery, second-copy restore, and real-client evidence MUST be produced on the selected formal host before that host is approved.

#### Scenario: macOS evidence exists but Windows is untested
- **WHEN** a future Windows host has not completed its native staging and formal UAT
- **THEN** macOS evidence does not satisfy the Windows acceptance gate
- **AND** the Windows adapter remains supported but unapproved for formal use
