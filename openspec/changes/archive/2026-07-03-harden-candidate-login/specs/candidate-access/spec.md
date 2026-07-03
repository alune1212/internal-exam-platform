## MODIFIED Requirements

### Requirement: Candidate Login
The system SHALL authenticate candidates with a two-step email OTP flow before issuing a candidate token. A challenge request MUST match an active candidate by name and roster email, with a matching employee number when provided, and MUST NOT issue a candidate token until a valid OTP is verified. Phone suffix alone MUST NOT be sufficient to authenticate a candidate in strict login mode.

#### Scenario: Candidate requests login OTP with matching identity
- **GIVEN** an active candidate record exists with a valid email
- **WHEN** the candidate submits matching name and email, with a matching employee number when provided
- **THEN** the system creates a short-lived email OTP challenge
- **AND** the system sends the OTP to the matched roster email
- **AND** the response does not include a candidate token

#### Scenario: Candidate verifies valid login OTP
- **GIVEN** an unexpired unused login challenge exists for an active candidate
- **WHEN** the candidate submits the correct OTP for that challenge
- **THEN** the system consumes the challenge
- **AND** the system returns a signed candidate token for that candidate

#### Scenario: Candidate identity does not match
- **GIVEN** no active candidate record matches the submitted login identity
- **WHEN** the candidate requests a login OTP
- **THEN** the system does not issue a candidate token
- **AND** the system does not create a usable challenge for another candidate

#### Scenario: Candidate submits invalid or expired OTP
- **GIVEN** a login challenge is expired, already consumed, attempt-exhausted, or receives an incorrect OTP
- **WHEN** the candidate submits OTP verification
- **THEN** the system rejects verification without issuing a candidate token

## ADDED Requirements

### Requirement: Candidate Login Challenge Controls
The system MUST store candidate login challenges with password-like OTP hygiene: OTP values MUST NOT be stored in plaintext, challenges MUST expire quickly, challenges MUST be single-use, verification attempts MUST be limited, and resend MUST invalidate any previous unconsumed challenge for the same candidate login.

#### Scenario: OTP is stored for verification
- **WHEN** the system creates a candidate login challenge
- **THEN** it stores only a hash or verifier for the OTP
- **AND** it stores expiration, consumption, attempt-count, and candidate association metadata

#### Scenario: Candidate requests a replacement OTP
- **GIVEN** an unconsumed login challenge exists for a candidate
- **WHEN** the candidate requests a new OTP with matching identity
- **THEN** the system invalidates the previous unconsumed challenge
- **AND** the system sends a new OTP for a new challenge

#### Scenario: Challenge attempt limit is reached
- **GIVEN** a login challenge has reached the allowed verification attempt limit
- **WHEN** the candidate submits another OTP verification attempt
- **THEN** the system rejects the attempt without issuing a candidate token

### Requirement: Candidate Login Rate Limiting
The system MUST apply public login rate limiting to candidate OTP request and verification endpoints using request source and normalized candidate identifiers.

#### Scenario: Repeated OTP requests exceed the limit
- **GIVEN** a client repeatedly requests candidate login OTPs within the configured rate-limit window
- **WHEN** the request count exceeds the allowed threshold
- **THEN** the system rejects further OTP requests with a rate-limit response

#### Scenario: Repeated OTP verification attempts exceed the limit
- **GIVEN** a client repeatedly submits OTP verification attempts within the configured rate-limit window
- **WHEN** the request count exceeds the allowed threshold
- **THEN** the system rejects further verification attempts with a rate-limit response
