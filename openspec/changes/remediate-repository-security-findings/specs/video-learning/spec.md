## ADDED Requirements

### Requirement: Authorized Learning Media Playback
Learning video bytes MUST NOT be served from a public static alias. Candidate learning responses MUST provide only a short-lived HMAC-signed playback URL bound to the candidate and video. The playback endpoint MUST verify that binding, recheck the candidate's active status and the video's published status, and resolve the stored media key beneath the configured storage root before returning the file with range support.

#### Scenario: Active candidate plays a published video
- **GIVEN** an active candidate obtains a playback URL for a published learning video
- **WHEN** the candidate requests that URL, including a valid unexpired playback credential
- **THEN** the service returns only the bound media file and supports byte-range playback
- **AND** the response prevents shared or stale caching

#### Scenario: Playback credential is invalid or lifecycle state changes
- **WHEN** the playback credential is missing, expired, tampered with, bound to another video, or the candidate is inactive
- **THEN** the service rejects the request without returning media bytes
- **WHEN** the video is archived or its stored key is missing or outside the configured storage root
- **THEN** the service rejects the request without returning media bytes

#### Scenario: Legacy static media path is requested
- **WHEN** a client requests a path under `/media/learning/` through either gateway
- **THEN** the gateway returns not found and does not read the learning-media volume

### Requirement: Bounded Learning Progress State
Learning progress updates MUST apply the existing candidate rate limit before loading or locking progress state and MUST enforce a fixed maximum number of normalized watched intervals. An update that would exceed the interval cap MUST be rejected before changing the progress row.

#### Scenario: Progress update exceeds the watched-interval cap
- **GIVEN** a candidate's progress already contains the maximum supported number of disjoint watched intervals
- **WHEN** the candidate submits a progress range that would add another interval
- **THEN** the system returns the stable conflict response before persisting the range
- **AND** the existing progress row remains unchanged

#### Scenario: Candidate repeats progress updates too quickly
- **GIVEN** a valid active candidate token
- **WHEN** progress requests exceed the existing candidate rate limit
- **THEN** the system returns the stable rate-limit response before loading progress state

### Requirement: Bounded Learning Catalog Reads
Authenticated candidate learning-catalog reads MUST use stable SQL pagination with a non-negative bounded offset, a page size no greater than 100, and the existing candidate rate limit before loading videos, progress, playback credentials, or response objects.

#### Scenario: Candidate reads a learning-catalog page
- **GIVEN** a valid token for an active candidate
- **WHEN** the candidate requests a valid learning-catalog page
- **THEN** the response contains no more than 100 published videos in stable order
- **AND** the service loads only the requested page and its associated progress

#### Scenario: Candidate requests an oversized or repeated catalog read
- **GIVEN** a valid active candidate token
- **WHEN** the candidate supplies an invalid oversized offset or exceeds the existing candidate rate limit
- **THEN** the system returns the stable validation or rate-limit response before loading the catalog
