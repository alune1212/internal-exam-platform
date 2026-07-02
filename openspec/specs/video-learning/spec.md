# Video Learning Specification

## Purpose

Video learning covers locally uploaded learning videos, candidate watch progress, and administrator learning completion reports. It is independent from exam eligibility, exam attempts, practice answers, scoring, ranking, and exam reports.

## Requirements

### Requirement: Admin Local Video Management
The system SHALL allow authenticated administrators to manage locally uploaded learning videos independently from exam configuration.

#### Scenario: Administrator uploads a supported video
- **GIVEN** an authenticated administrator provides video metadata and a supported local video file within the configured upload limits
- **WHEN** the administrator submits the upload
- **THEN** the system stores the file using a server-generated storage key
- **AND** the system persists video metadata including title, original filename, content type, file size, duration, status, and completion threshold

#### Scenario: Uploaded file is invalid
- **GIVEN** an authenticated administrator provides an unsupported file type, missing duration, empty title, or file larger than the configured upload limit
- **WHEN** the administrator submits the upload
- **THEN** the system rejects the upload without creating a published learning video record

#### Scenario: Administrator publishes or archives video
- **GIVEN** a learning video exists
- **WHEN** an authenticated administrator changes its status to published or archived
- **THEN** the system updates the video status without changing any exam configuration or attempt data

### Requirement: Candidate Learning Video Access
The system SHALL expose published learning videos to authenticated active candidates through candidate-token-gated learning APIs.

#### Scenario: Candidate lists learning videos
- **GIVEN** a valid candidate token for an active candidate and published learning videos exist
- **WHEN** the candidate requests the learning video list
- **THEN** the response includes published videos with the candidate's progress and completion status

#### Scenario: Candidate opens a learning video
- **GIVEN** a valid candidate token for an active candidate and a published learning video exists
- **WHEN** the candidate requests the video detail
- **THEN** the response includes metadata, playback location, the 90 percent completion threshold, and the candidate's current progress

#### Scenario: Candidate is unauthenticated or inactive
- **GIVEN** the request has no valid active candidate identity
- **WHEN** the request targets a candidate learning API
- **THEN** the system rejects the request without returning learning video metadata or progress

#### Scenario: Candidate requests archived video
- **GIVEN** a learning video is archived
- **WHEN** a candidate requests the video list or detail
- **THEN** the archived video is omitted or rejected from candidate-facing responses

### Requirement: Ninety Percent Watch Completion
The system SHALL track candidate video progress and mark a learning video complete only when watched progress reaches at least 90 percent of the stored video duration.

#### Scenario: Candidate reports normal playback progress
- **GIVEN** a candidate is watching a published learning video
- **WHEN** the frontend sends a progress heartbeat with the current playback position
- **THEN** the system persists the candidate's last position, watched progress, completion percentage, and latest heartbeat time

#### Scenario: Candidate reaches completion threshold
- **GIVEN** a candidate has accumulated watched progress of at least 90 percent of the stored video duration
- **WHEN** the system processes the progress update
- **THEN** the system records the learning video as completed for that candidate

#### Scenario: Candidate seeks ahead without watching skipped content
- **GIVEN** a candidate jumps from an earlier playback position to a later playback position
- **WHEN** the frontend reports the later playback position
- **THEN** the system MUST NOT count the skipped interval as watched progress solely because the playback position advanced

#### Scenario: Candidate rewatches the same interval
- **GIVEN** a candidate has already received watched progress for a video interval
- **WHEN** the candidate watches the same interval again
- **THEN** the system MUST NOT double-count that interval toward the 90 percent completion threshold

### Requirement: Admin Learning Completion Reporting
The system SHALL allow authenticated administrators to review candidate learning completion status independently from exam reports.

#### Scenario: Administrator views video completion report
- **GIVEN** learning videos, candidates, and progress records exist
- **WHEN** an authenticated administrator requests the learning completion report
- **THEN** the response includes candidate identity fields, video metadata, completion percentage, completion status, last progress time, and completion time

#### Scenario: Administrator filters learning report by video or status
- **GIVEN** learning completion data exists for multiple videos and candidates
- **WHEN** an authenticated administrator applies video or completion-status filters
- **THEN** the response includes only rows matching the selected learning filters

#### Scenario: Administrator exports learning report
- **GIVEN** learning completion report data is available
- **WHEN** an authenticated administrator downloads the learning report export
- **THEN** the system returns an Excel workbook with escaped cells and the same learning report scope as the current filters

### Requirement: Learning Is Independent From Exams
The system MUST keep video learning progress independent from formal exams, practice answers, exam ranking, and exam reports.

#### Scenario: Candidate has not completed video learning
- **GIVEN** a candidate has not completed any learning video
- **WHEN** the candidate requests active exams or starts an eligible exam
- **THEN** the system preserves existing exam eligibility behavior and does not block the candidate because of learning progress

#### Scenario: Candidate completes video learning
- **GIVEN** a candidate completes one or more learning videos
- **WHEN** the system calculates exam scores, rankings, retake eligibility, or practice answer records
- **THEN** video learning progress does not alter those exam or practice results

#### Scenario: Administrator changes learning video status
- **GIVEN** an administrator publishes, edits, or archives a learning video
- **WHEN** existing exam attempts or exam configurations are later read
- **THEN** the system preserves existing exam snapshot, fixed-paper, scoring, and report behavior
