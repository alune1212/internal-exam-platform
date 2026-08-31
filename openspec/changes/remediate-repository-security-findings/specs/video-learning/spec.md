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
