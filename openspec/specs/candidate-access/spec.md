# Candidate Access Specification

## Purpose

Candidate access covers candidate login, candidate-scoped exam discovery, and practice API access.

## Requirements

### Requirement: Candidate Login
The system SHALL authenticate candidates with a two-step email OTP flow before issuing a candidate token. A challenge request MUST match an active candidate by name and roster email, with a matching employee number when provided, and MUST NOT issue a candidate token until a valid OTP is verified. Phone suffix alone MUST NOT be sufficient to authenticate a candidate in strict login mode. Challenge state MUST be committed before email delivery begins, challenge requests MUST keep a uniform response for matched and unmatched identities, and transient delivery failures MUST use bounded retry without leaking candidate or delivery secrets. SMTP delivery MUST support mutually exclusive STARTTLS and implicit SSL transports.

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
- **AND** the system does not send an email
- **AND** the system does not create a usable challenge for another candidate
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

#### Scenario: SMTP server requires implicit SSL
- **GIVEN** candidate OTP delivery is configured for an implicit SSL SMTP port
- **WHEN** the system opens the SMTP connection
- **THEN** it uses SSL from connection establishment without issuing STARTTLS
- **AND** it authenticates and sends through the encrypted connection

#### Scenario: SMTP transport configuration conflicts
- **GIVEN** both implicit SSL and STARTTLS are enabled, or authenticated SMTP has only one of username and password
- **WHEN** startup validation runs
- **THEN** the system rejects the configuration without printing credential values

### Requirement: Uniform Candidate Login Challenge Response
The system MUST return the same response envelope and status code for every candidate login challenge request, regardless of whether the candidate identity was found, ambiguous, inactive, missing an email, or encountered an internal delivery failure. Valid and invalid lookup outcomes MUST follow the same challenge creation and response path so the public API does not reveal roster membership through differentiated behavior.

#### Scenario: Unknown identity produces a uniform response
- **GIVEN** a request whose identity does not match any active candidate
- **WHEN** the system processes the challenge request
- **THEN** the response status and body shape match the response for a valid candidate
- **AND** the only operational differences are the audit log entry and the absence of an email send

#### Scenario: Ambiguous identity produces a uniform response
- **GIVEN** a request whose identity matches more than one active candidate
- **WHEN** the system processes the challenge request
- **THEN** the response status and body shape match the response for a valid candidate
- **AND** the response does not indicate the ambiguity

#### Scenario: Inactive or missing-email identity produces a uniform response
- **GIVEN** a matching candidate is inactive or has no usable email
- **WHEN** the system processes the challenge request
- **THEN** the response status and body shape match the response for a valid candidate
- **AND** the system does not send an email

### Requirement: Sentinel Candidate for Unknown Identities
The system MUST persist login challenges for unknown, ambiguous, inactive, or missing-email identities against the single designated candidate row marked `is_login_sentinel`. The sentinel MUST remain inactive, MUST NOT have a usable email, MUST never be scoped to an exam, MUST never issue a candidate token, and MUST be excluded from candidate-facing lists and imports.

#### Scenario: Unknown identity creates a challenge against the sentinel
- **WHEN** the system processes a challenge request whose identity does not resolve to a real candidate
- **THEN** it creates a `CandidateLoginChallenge` whose candidate is marked `is_login_sentinel`
- **AND** it does not send an email for the sentinel challenge
- **AND** it rejects later OTP verification against the sentinel challenge without issuing a candidate token

#### Scenario: Sentinel candidate is never scoped to an exam
- **WHEN** an administrator, import, or service attempts to add the sentinel candidate to an exam scope
- **THEN** the system rejects or excludes the sentinel candidate

### Requirement: Audit Log for Unknown-Identity Login Attempts
The system MUST emit one structured audit log entry for every challenge request whose identity does not resolve to a valid active candidate with email, including unknown, ambiguous, inactive, and missing-email outcomes. The log MUST be protected by the same public request rate limit, MUST contain only hashed identity and request-source data, and MUST NOT be exposed through the public API.

#### Scenario: Unknown identity is logged for audit
- **WHEN** lookup resolves to an unknown, ambiguous, inactive, or missing-email outcome
- **THEN** the system emits a structured `candidate_login.unknown_identity` log entry with hashed identity fields
- **AND** the log contains no plaintext name, email, employee number, OTP, or SMTP credential

#### Scenario: Audit signal is not exposed through the API
- **WHEN** a client submits an invalid identity challenge request
- **THEN** the public response remains uniform
- **AND** the lookup outcome is observable only through protected operational logs

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

### Requirement: Candidate-Scoped Active Exams
The system SHALL require X-Candidate-Token for active exam listing and SHALL only return active exams in the candidate's exam scope that the candidate can still enter.

#### Scenario: Candidate has an eligible active exam
- **GIVEN** a valid candidate token and an active exam containing the candidate in exam_candidate_scope
- **WHEN** the candidate requests active exams
- **THEN** the response includes that exam with server-calculated availability status

#### Scenario: Candidate already submitted without retake grant
- **GIVEN** a candidate has submitted an exam and has no unused retake grant
- **WHEN** the candidate requests active exams
- **THEN** the submitted exam is excluded from the active exam list

### Requirement: Practice API Privacy
The system MUST require X-Candidate-Token for practice APIs and MUST NOT expose correct answers, analysis, correctness, or score in practice question or submit responses.

#### Scenario: Candidate lists practice questions
- **GIVEN** a valid candidate token
- **WHEN** the candidate requests practice questions
- **THEN** the response omits correct answers and analysis

#### Scenario: Candidate submits practice answer
- **GIVEN** a valid candidate token
- **WHEN** the candidate submits a practice answer
- **THEN** the response omits correct answer, analysis, correctness, and score while the server may persist practice result data
