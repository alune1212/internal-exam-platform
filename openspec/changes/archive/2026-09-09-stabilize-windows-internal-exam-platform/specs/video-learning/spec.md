## ADDED Requirements

### Requirement: Learning Mutation Write Gate
Video upload, edit, publish, and archive operations MUST be rejected while a formal attempt is in progress or while the coordinated backup write-freeze lock is active. Candidate video listing and playback reads SHALL remain available subject to existing authentication and status rules.

#### Scenario: Operator uploads during a formal exam
- **GIVEN** a formal attempt is in progress
- **WHEN** an authenticated operator uploads or mutates a learning video
- **THEN** the system rejects the mutation with a stable conflict response
- **AND** does not create partial database or media state

#### Scenario: Learning progress writes meet backup freeze
- **GIVEN** the backup operation owns the write-freeze lock
- **WHEN** a candidate progress heartbeat arrives
- **THEN** the system returns a retryable response without corrupting existing progress
- **AND** playback reads remain available

#### Scenario: Learning access occurs outside protected mutation
- **WHEN** an authenticated active candidate lists or plays a published video
- **THEN** existing video-access and 90-percent completion semantics remain unchanged

### Requirement: Learning Media Disk Reserve
Before accepting a new learning-video upload, the system MUST verify that the proposed upload preserves at least 20 GiB of free formal-host storage and at least three times the current combined database and media footprint.

#### Scenario: Upload preserves reserve
- **WHEN** the proposed validated upload leaves both required reserve thresholds satisfied
- **THEN** the existing video upload validation and persistence flow may proceed

#### Scenario: Upload violates reserve
- **WHEN** the proposed upload would violate either reserve threshold
- **THEN** the system rejects it before persisting the final video record or storage object
- **AND** reports a non-sensitive capacity message to the local operator
