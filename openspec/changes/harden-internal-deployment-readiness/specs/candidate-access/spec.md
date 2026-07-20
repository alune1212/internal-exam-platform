## MODIFIED Requirements

### Requirement: Candidate Login
The system SHALL authenticate candidates with a two-step email OTP flow before issuing a candidate token. A challenge request MUST match an active candidate by name and roster email, with a matching employee number when provided, and MUST NOT issue a candidate token until a valid OTP is verified. Phone suffix alone MUST NOT be sufficient to authenticate a candidate in strict login mode. Challenge state MUST be committed before email delivery begins, challenge requests MUST keep a uniform response for matched and unmatched identities, and transient delivery failures MUST use bounded retry without leaking candidate or delivery secrets.

#### Scenario: Candidate requests login OTP with matching identity
- **GIVEN** an active candidate record exists with a valid email
- **WHEN** the candidate submits matching name and email, with a matching employee number when provided
- **THEN** the system commits a short-lived email OTP challenge before scheduling delivery
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
- **THEN** the system returns the same challenge response shape used for a matched identity
- **AND** the system does not send an email or create a usable challenge for another candidate
- **AND** the system does not issue a candidate token

#### Scenario: Candidate submits invalid or expired OTP
- **GIVEN** a login challenge is expired, already consumed, attempt-exhausted, or receives an incorrect OTP
- **WHEN** the candidate submits OTP verification
- **THEN** the system rejects verification without issuing a candidate token

#### Scenario: Transient email delivery fails
- **GIVEN** a committed challenge for a matched candidate and a transient SMTP or network failure
- **WHEN** background OTP delivery runs
- **THEN** the system retries delivery only up to the bounded attempt limit with short backoff
- **AND** the original login response is not changed to a differentiated error

#### Scenario: Email delivery fails permanently
- **GIVEN** a committed challenge whose delivery reaches a permanent failure or exhausts bounded retry
- **WHEN** the system records the final delivery failure
- **THEN** the log identifies the event and challenge without recording the OTP, recipient email, SMTP password, or full submitted identity
- **AND** the candidate may request a replacement challenge after the configured cooldown
