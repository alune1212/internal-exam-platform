## ADDED Requirements

### Requirement: Twelve-Month Online Retention
The system SHALL identify exam-scoped personal, attempt, answer, result, and evidence records for archival deletion after 12 months from final activity while protecting active or still-referenced records.

#### Scenario: Historical exam reaches retention age
- **GIVEN** an exam and its final activity are older than 12 months
- **WHEN** the retention preview runs
- **THEN** it lists the exam and affected record counts as eligible without deleting them

#### Scenario: Record is still active or referenced
- **GIVEN** an exam, candidate, question, video, or related record is active or required by retained data
- **WHEN** retention eligibility is calculated
- **THEN** the system excludes that record from unsafe deletion and explains the non-sensitive reason

### Requirement: Confirmed Archival Deletion
Retention deletion MUST require a preview, versioned export and manifest, a verified paired backup, explicit exam identifiers, operator confirmation, and audit recording. The system MUST NOT silently delete expired records.

#### Scenario: Operator confirms eligible exams
- **GIVEN** the preview is current, the archive export is complete, and a paired backup is verified
- **WHEN** the operator confirms explicit eligible exam IDs
- **THEN** the system deletes the permitted online records transactionally
- **AND** records the result and counts in the audit trail

#### Scenario: Required safeguard is missing
- **GIVEN** the preview is stale, the archive or backup is missing, an ID is not eligible, or referential checks fail
- **WHEN** deletion is requested
- **THEN** no target exam data is deleted

### Requirement: Opportunistic Paired Backup
The system SHALL attempt a paired PostgreSQL and learning-media backup daily when data changed. It MUST obtain a bounded write-freeze lock and MUST skip rather than force backup when a formal attempt is in progress or the lock cannot be acquired.

#### Scenario: Daily backup can run safely
- **GIVEN** relevant data changed, no formal attempt is in progress, and no protected write is active
- **WHEN** the daily backup task obtains the operational lock
- **THEN** new protected writes receive a retryable response while reads remain available
- **AND** the task creates and validates the paired backup before releasing the lock

#### Scenario: Formal exam or lock conflict exists
- **WHEN** the daily backup task detects an in-progress formal attempt or cannot obtain the operational lock
- **THEN** it records a skipped result
- **AND** it does not interrupt the exam or force a backup

#### Scenario: Backup process crashes
- **GIVEN** the backup owner stops before releasing its lock
- **WHEN** the lock expiry passes
- **THEN** normal writes recover without manual database editing

### Requirement: Local And Encrypted Second-Copy Retention
The formal host SHALL retain the latest three verified local backups. A configured encrypted second storage location SHALL retain each final post-exam backup for 12 months, while partial or unverified backups MUST NOT enter either formal retention set.

#### Scenario: Verified backup is retained
- **WHEN** a complete backup passes checksums and restore validation requirements
- **THEN** it is eligible for local retention and second-copy synchronization
- **AND** local pruning preserves the latest three verified backups

#### Scenario: Second copy is unavailable or unprotected
- **WHEN** the configured second storage cannot be reached or its required protection cannot be confirmed
- **THEN** the system records the synchronization as failed
- **AND** it does not report the backup as having a valid second copy

### Requirement: Second-Copy Restore Drill
The first formal Windows release and each subsequent quarter MUST restore from the second-copy artifact into disposable database and media resources and verify migration head, representative counts, archive integrity, and readable media samples.

#### Scenario: Quarterly restore succeeds
- **WHEN** a selected second-copy backup is restored into a disposable project
- **THEN** all required database and media checks pass
- **AND** disposable resources are removed without changing the formal project

#### Scenario: Restore drill fails
- **WHEN** any checksum, restore, migration, count, or media-read check fails
- **THEN** the selected artifact is not accepted as proven recoverable
- **AND** the formal project is not overwritten

### Requirement: Dynamic Disk Safety Reserve
The platform MUST preserve at least 20 GiB of free formal-host storage and at least three times the current combined database and media footprint before accepting a new video upload or release upgrade.

#### Scenario: Storage reserve is sufficient
- **WHEN** an upload or upgrade preflight calculates both reserve thresholds as satisfied after the proposed operation
- **THEN** the operation may proceed subject to its other gates

#### Scenario: Storage reserve would be violated
- **WHEN** a proposed upload or upgrade would reduce free space below either threshold
- **THEN** the operation is rejected with a non-sensitive capacity message
- **AND** ongoing formal answer save and submit traffic remains available

### Requirement: Lifecycle Evidence Integrity
Backup, restore, retention preview, archive, deletion, and synchronization operations MUST write checksummed non-secret manifests that identify the version, operator or task identity, timestamps, target identifiers, outcome, and artifact references. A cross-host cutover manifest MUST additionally identify `datasetId`, source/target `hostId`, previous/next `writerGeneration`, paired-backup checksums, and whole-source/target-project stop evidence.

#### Scenario: Lifecycle operation completes
- **WHEN** a lifecycle operation succeeds, fails, or is skipped
- **THEN** its manifest records the outcome and non-sensitive evidence needed for later review
- **AND** it contains no formal credential, token, OTP, or unrestricted personal-data payload

#### Scenario: Cutover manifest is incomplete
- **GIVEN** a cross-host manifest lacks `datasetId`, host identity, writer generation, paired-backup checksums, or whole-project stop evidence
- **WHEN** target acceptance is requested
- **THEN** `accept-cutover` rejects it without exposing candidate write traffic
