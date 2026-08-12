## MODIFIED Requirements

### Requirement: Candidate Learning Video Access
The system SHALL expose published learning videos to every authenticated active platform account through candidate-token-gated learning APIs. Formal-exam scope, invitation delivery, and roster status MUST NOT be required for learning access.

#### Scenario: Candidate lists learning videos
- **GIVEN** a valid candidate token for an active platform account and published learning videos exist
- **WHEN** the user requests the learning video list
- **THEN** the response includes published videos with that account's progress and completion status

#### Scenario: Candidate opens a learning video
- **GIVEN** a valid candidate token for an active platform account and a published learning video exists
- **WHEN** the user requests the video detail
- **THEN** the response includes metadata, playback location, the 90 percent completion threshold, and that account's current progress

#### Scenario: Candidate is unauthenticated or inactive
- **GIVEN** the request has no valid active platform-account identity
- **WHEN** the request targets a candidate learning API
- **THEN** the system rejects the request without returning learning video metadata or progress

#### Scenario: Candidate requests archived video
- **GIVEN** a learning video is archived
- **WHEN** an active account requests the video list or detail
- **THEN** the archived video is omitted or rejected from candidate-facing responses

### Requirement: Ninety Percent Watch Completion
The system SHALL track learning-video progress per platform account and mark a video complete only when watched progress reaches at least 90 percent of the stored video duration.

#### Scenario: Candidate reports normal playback progress
- **GIVEN** an active account is watching a published learning video
- **WHEN** the frontend sends a progress heartbeat with the current playback position
- **THEN** the system persists that account's last position, watched progress, completion percentage, and latest heartbeat time

#### Scenario: Candidate reaches completion threshold
- **GIVEN** an account has accumulated watched progress of at least 90 percent of the stored video duration
- **WHEN** the system processes the progress update
- **THEN** the system records the learning video as completed for that account

#### Scenario: Candidate seeks ahead without watching skipped content
- **GIVEN** an account jumps from an earlier playback position to a later playback position
- **WHEN** the frontend reports the later playback position
- **THEN** the system MUST NOT count the skipped interval as watched progress solely because the playback position advanced

#### Scenario: Candidate rewatches the same interval
- **GIVEN** an account has already received watched progress for a video interval
- **WHEN** the account watches the same interval again
- **THEN** the system MUST NOT double-count that interval toward the 90 percent completion threshold

### Requirement: Admin Learning Completion Reporting
The system SHALL allow authenticated administrators to review platform-account learning completion independently from exam reports. Learning rows SHALL use normalized account email, editable display name, and lifecycle status and MUST NOT expose `employee_no`, `phone_suffix`, global `should_attend`, or exam-scoped roster organization as account identity.

#### Scenario: Administrator views video completion report
- **GIVEN** learning videos, platform accounts, and progress records exist
- **WHEN** an authenticated administrator requests the learning completion report
- **THEN** the response includes account email/display name/status, video metadata, completion percentage, completion status, last progress time, and completion time
- **AND** it does not substitute a frozen exam-roster identity for the general learning identity

#### Scenario: Administrator filters learning report by video or status
- **GIVEN** learning completion data exists for multiple videos and accounts
- **WHEN** an authenticated administrator applies video or completion-status filters
- **THEN** the response includes only rows matching the selected learning filters

#### Scenario: Administrator exports learning report
- **GIVEN** learning completion report data is available
- **WHEN** an authenticated administrator downloads the learning report export
- **THEN** the system returns an Excel workbook with escaped cells and the same learning report scope as the current filters
- **AND** the identity columns contain no removed employee, phone, or global-attendance fields
