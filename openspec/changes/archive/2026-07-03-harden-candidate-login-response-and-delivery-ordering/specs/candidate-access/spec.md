## MODIFIED Requirements

### Requirement: Candidate Login
The system SHALL authenticate candidates with a two-step email OTP flow before issuing a candidate token. A challenge request MUST match an active candidate by name and roster email, with a matching employee number when provided, and MUST NOT issue a candidate token until a valid OTP is verified. Phone suffix alone MUST NOT be sufficient to authenticate a candidate in strict login mode. The challenge request endpoint MUST return a uniform success response regardless of lookup outcome, and MUST commit the challenge row before triggering any email delivery, so that neither lookup nor delivery outcomes are observable to the caller.

#### Scenario: Candidate requests login OTP with matching identity
- **GIVEN** an active candidate record exists with a valid email
- **WHEN** the candidate submits matching name and email, with a matching employee number when provided
- **THEN** the system creates a short-lived email OTP challenge
- **AND** the system persists and commits the challenge row before invoking any email delivery
- **AND** the system enqueues the email send to run after the response is sent
- **AND** the response does not include a candidate token

#### Scenario: Candidate identity does not match
- **GIVEN** no active candidate record matches the submitted login identity
- **WHEN** the candidate requests a login OTP
- **THEN** the system returns a uniform success response with a challenge id and short fixed TTL
- **AND** the system does not issue a candidate token
- **AND** the system does not send an email
- **AND** the system records a single rate-limited audit log entry for the unknown-identity attempt

#### Scenario: Candidate identity matches multiple records
- **GIVEN** more than one active candidate record matches the submitted login identity
- **WHEN** the candidate requests a login OTP
- **THEN** the system returns a uniform success response with a challenge id and short fixed TTL
- **AND** the system does not issue a candidate token
- **AND** the system does not send an email
- **AND** the system records a single rate-limited audit log entry for the ambiguous-identity attempt

#### Scenario: Candidate identity is inactive or has no email
- **GIVEN** a candidate record matches the identity but the candidate is inactive or has no usable email
- **WHEN** the candidate requests a login OTP
- **THEN** the system returns a uniform success response with a challenge id and short fixed TTL
- **AND** the system does not issue a candidate token
- **AND** the system does not send an email
- **AND** the system records a single rate-limited audit log entry for the inactive-or-no-email attempt

#### Scenario: Email delivery fails after the challenge is committed
- **GIVEN** a challenge row has been committed for a valid candidate identity
- **WHEN** the post-commit email delivery fails
- **THEN** the system does not surface the delivery error to the caller
- **AND** the challenge row remains valid and reusable
- **AND** the system logs the delivery failure for operator review

#### Scenario: Candidate verifies valid login OTP
- **GIVEN** an unexpired unused login challenge exists for an active candidate
- **WHEN** the candidate submits the correct OTP for that challenge
- **THEN** the system consumes the challenge
- **AND** the system returns a signed candidate token for that candidate

#### Scenario: Candidate submits invalid or expired OTP
- **GIVEN** a login challenge is expired, already consumed, attempt-exhausted, or receives an incorrect OTP
- **WHEN** the candidate submits OTP verification
- **THEN** the system rejects verification without issuing a candidate token

## ADDED Requirements

### Requirement: Uniform Candidate Login Challenge Response
The system MUST return the same response envelope, status code, and observable timing for every candidate login challenge request, regardless of whether the candidate identity was found, ambiguous, inactive, missing an email, or hit an internal delivery failure. The challenge request response MUST NOT reveal the lookup outcome through the HTTP status, response body, or wall-clock timing.

#### Scenario: Unknown identity produces a uniform response
- **GIVEN** a request whose identity does not match any active candidate
- **WHEN** the system processes the challenge request
- **THEN** the response status, body shape, and timing match the response for a valid candidate
- **AND** the only observable difference between valid and invalid requests is the audit log entry and the absence of an email send

#### Scenario: Ambiguous identity produces a uniform response
- **GIVEN** a request whose identity matches more than one active candidate
- **WHEN** the system processes the challenge request
- **THEN** the response status, body shape, and timing match the response for a valid candidate
- **AND** the response does not indicate the ambiguity

### Requirement: Sentinel Candidate for Unknown Identities
The system MUST persist `CandidateLoginChallenge` rows for unknown, ambiguous, inactive, or missing-email identities against a designated sentinel candidate that is never scoped to any exam, never issues a candidate token, and never receives an email. The sentinel candidate id MUST be configurable and MUST be excluded from any candidate-facing list, search, or scope assignment.

#### Scenario: Unknown identity creates a challenge against the sentinel
- **WHEN** the system processes a challenge request whose identity does not resolve to a real candidate
- **THEN** the system creates a `CandidateLoginChallenge` row whose `candidate_id` is the sentinel id
- **AND** the system does not send an email for the sentinel challenge
- **AND** the system rejects any later OTP verification against the sentinel challenge without issuing a candidate token

#### Scenario: Sentinel candidate is never scoped to an exam
- **WHEN** an administrator creates or modifies an exam-candidate scope
- **THEN** the system rejects any attempt to scope the sentinel candidate to an exam

### Requirement: Audit Log for Unknown-Identity Login Attempts
The system MUST emit a single structured audit log entry for every challenge request whose identity does not resolve to a valid active candidate with email, including unknown, ambiguous, inactive, and missing-email outcomes. The log entry MUST be rate-limited through the same public token rate limiter that protects the challenge endpoint, MUST NOT contain plaintext identity fields, and MUST be queryable by operators without exposing identity data to API callers.

#### Scenario: Unknown identity is logged for audit
- **WHEN** the system rejects a lookup outcome for an unknown, ambiguous, inactive, or missing-email identity
- **THEN** the system emits a structured log line with a fixed event name and hashed identity fields
- **AND** the log line is suppressed if the request was already rejected by the rate limiter

#### Scenario: Log line is not exposed through the API
- **WHEN** an attacker submits repeated challenge requests
- **THEN** the response body and timing remain uniform
- **AND** the audit signal is observable only through structured logs, not through the public API
