## MODIFIED Requirements

### Requirement: Candidate Login
The system SHALL authenticate users through one email-only OTP challenge for both login and registration before issuing any candidate token. For every syntactically valid normalized email, the challenge request MUST commit challenge state before delivery and MUST attempt delivery whether the email belongs to an active account, a pending account, an inactive account, or no account yet. A valid OTP for an existing active account MUST return the existing signed candidate token directly; a valid OTP for a new or pending account MUST return only a short-lived, single-use registration-completion credential until a display name is confirmed. Candidate tokens MUST be issued only to active accounts, MUST expire no later than four hours after issuance, and MUST NOT be issued from a name, employee number, phone suffix, sentinel row, or unverified registration credential. SMTP delivery MUST support the configured mutually exclusive STARTTLS and implicit SSL transports.

#### Scenario: Candidate requests login OTP with matching identity
- **GIVEN** an active platform account has a valid normalized email
- **WHEN** the user submits that email to the login endpoint
- **THEN** the system commits a short-lived six-digit email OTP challenge before delivery
- **AND** it attempts to send the OTP to that email
- **AND** the response does not include a candidate token

#### Scenario: Unknown valid email receives an OTP
- **GIVEN** no platform account exists for a syntactically valid normalized email
- **WHEN** the user requests an email OTP
- **THEN** the system commits a challenge and sends the OTP to the requested mailbox
- **AND** the response has the same challenge envelope as an existing-account request
- **AND** no formal-exam scope is granted by the delivery

#### Scenario: Candidate verifies valid login OTP
- **GIVEN** an unexpired unused OTP challenge belongs to an active account
- **WHEN** the user submits the correct OTP
- **THEN** the system consumes the challenge
- **AND** it returns the existing direct signed candidate token with a lifetime of no more than four hours

#### Scenario: New email verifies a valid OTP
- **GIVEN** an unexpired unused OTP challenge belongs to a new or pending email account
- **WHEN** the user submits the correct OTP
- **THEN** the system consumes the challenge
- **AND** it returns a one-time registration-completion credential
- **AND** it does not return a candidate token until the user confirms a display name

#### Scenario: Candidate identity does not match
- **GIVEN** no active platform account matches a syntactically valid normalized email
- **WHEN** the candidate requests a login OTP
- **THEN** the system returns the same challenge response shape used for an existing account
- **AND** it sends the OTP to the requested mailbox
- **AND** it does not issue a candidate token before registration completion

#### Scenario: Inactive account verifies a valid OTP
- **GIVEN** an unexpired unused OTP challenge belongs to an inactive account
- **WHEN** the user submits the correct OTP
- **THEN** the system consumes the challenge and returns a stable account-unavailable outcome
- **AND** it issues neither a candidate token nor a registration-completion credential

#### Scenario: Candidate submits invalid or expired OTP
- **GIVEN** a login challenge is expired, already consumed, attempt-exhausted, or receives an incorrect OTP
- **WHEN** the user submits OTP verification
- **THEN** the system rejects verification without issuing a candidate token

#### Scenario: Transient email delivery fails
- **GIVEN** a challenge row has been committed for a valid email
- **WHEN** post-commit SMTP or network delivery fails transiently
- **THEN** the system retries delivery only up to the bounded attempt limit with short backoff
- **AND** the original login response remains uniform and does not surface a differentiated delivery error

#### Scenario: Email delivery fails permanently
- **GIVEN** a committed challenge whose delivery reaches a permanent failure or exhausts bounded retry
- **WHEN** the system records the final delivery failure
- **THEN** the log identifies the event and challenge without recording the OTP, recipient email, SMTP password, or full submitted identity
- **AND** the user may request a replacement challenge after the configured cooldown

#### Scenario: Email delivery fails after challenge commit
- **GIVEN** a challenge row has been committed for a valid email
- **WHEN** post-commit delivery fails
- **THEN** the challenge response remains uniform and the challenge row is not rolled back

#### Scenario: SMTP server requires implicit SSL
- **GIVEN** candidate OTP delivery is configured for an implicit SSL SMTP port
- **WHEN** the system opens the SMTP connection
- **THEN** it uses SSL from connection establishment without issuing STARTTLS
- **AND** it authenticates and sends through the encrypted connection

#### Scenario: SMTP transport configuration conflicts
- **GIVEN** both implicit SSL and STARTTLS are enabled, or authenticated SMTP has only one of username and password
- **WHEN** startup validation runs
- **THEN** the system rejects the configuration without printing credential values

#### Scenario: Legacy identity fields are used
- **WHEN** a client supplies name, employee number, phone suffix, or a sentinel identifier instead of an email
- **THEN** the email-only request schema rejects the legacy contract
- **AND** no candidate token is issued from the legacy contract

### Requirement: Uniform Candidate Login Challenge Response
The system MUST return the same response envelope, status code, and observable timing for email OTP challenge requests for existing, new, pending, or inactive accounts and for any valid normalized email that has no account. Lookup status and post-commit delivery failure MUST NOT be revealed through the HTTP response; malformed email input MAY fail normal schema validation before a challenge is created.

#### Scenario: Unknown identity produces a uniform response
- **GIVEN** one request targets an active account and another targets a valid email with no account
- **WHEN** both requests pass email validation and rate limits
- **THEN** their challenge responses have the same status, envelope, and fixed TTL shape
- **AND** the new-email request still attempts actual OTP delivery

#### Scenario: Ambiguous identity produces a uniform response
- **GIVEN** legacy data or a migration anomaly would associate more than one row with an email
- **WHEN** the user requests an OTP
- **THEN** the response status, body shape, and timing remain the same as for a valid single account
- **AND** the system does not disclose the anomaly or issue a token from the ambiguous rows

#### Scenario: Inactive or missing-email identity produces a uniform response
- **GIVEN** a normalized email belongs to a pending or inactive account, or a legacy row lacks a usable email
- **WHEN** the user requests an OTP
- **THEN** the response does not disclose the account status
- **AND** the endpoint follows the same challenge response path as an active account

#### Scenario: Delivery failure does not create an enumeration oracle
- **GIVEN** two valid-email challenge requests where one post-commit delivery fails
- **WHEN** the endpoint returns
- **THEN** both callers receive the same response status and body shape
- **AND** delivery outcome remains available only to protected operational logging

### Requirement: Candidate Login Challenge Controls
The system MUST store email login challenges with password-like OTP hygiene: the six-digit OTP MUST NOT be stored in plaintext, each challenge MUST expire after ten minutes, each challenge MUST be single-use, verification attempts MUST be limited to five, and resend MUST be unavailable until the sixty-second cooldown and MUST invalidate any previous unconsumed challenge for the same normalized email.

#### Scenario: OTP is stored for verification
- **WHEN** the system creates an email login challenge
- **THEN** it stores only a hash or verifier for the OTP
- **AND** it stores expiration, consumption, attempt-count, normalized-email, and account-association metadata

#### Scenario: Candidate requests a replacement OTP
- **GIVEN** an unconsumed login challenge exists for a normalized email
- **WHEN** the user requests another OTP before or after the configured cooldown
- **THEN** a request before sixty seconds is rate-limited
- **AND** an accepted replacement invalidates the previous unconsumed challenge
- **AND** the system sends a new six-digit OTP for a new challenge

#### Scenario: Challenge attempt limit is reached
- **GIVEN** a login challenge has reached five failed verification attempts
- **WHEN** the user submits another OTP verification attempt
- **THEN** the system rejects the attempt without issuing a candidate token or registration credential

### Requirement: Candidate Login Rate Limiting
The system MUST apply configurable public login rate limiting to candidate OTP request and verification endpoints using request source and the normalized email, with independent per-email, per-source, and global send limits.

#### Scenario: Repeated OTP requests exceed the limit
- **GIVEN** a client repeatedly requests candidate OTPs for one normalized email within the configured window
- **WHEN** the per-email send limit is exceeded
- **THEN** the system rejects further OTP requests with a rate-limit response

#### Scenario: Repeated OTP requests exceed the source or global limit
- **GIVEN** traffic exceeds a configured source-wide or global send limit
- **WHEN** another candidate requests an OTP
- **THEN** the system rejects the request without sending an email
- **AND** it does not reveal whether the target email has an account

#### Scenario: Repeated OTP verification attempts exceed the limit
- **GIVEN** a client repeatedly submits OTP verification attempts within the configured rate-limit window
- **WHEN** the request count exceeds the allowed threshold
- **THEN** the system rejects further verification attempts with a rate-limit response

### Requirement: Candidate-Scoped Active Exams
The system SHALL require `X-Candidate-Token` for active exam listing and SHALL return a published active exam only when the token belongs to an active account with an immutable `exam_candidate_scope` for that exam. A scoped exam MUST be visible immediately after publication, including its `available_from` and an upcoming/not-yet-open status, while start, resume, attempt access, and result access MUST continue to enforce the exam's timing, attempt, release, and retake rules.

#### Scenario: Candidate has an eligible active exam
- **GIVEN** a valid four-hour candidate token and a published active exam containing that account in `exam_candidate_scope`
- **WHEN** the candidate requests active exams
- **THEN** the response includes that exam with server-calculated availability status

#### Scenario: Scoped exam is visible before opening
- **GIVEN** the account is scoped to a published exam whose `available_from` is in the future
- **WHEN** the candidate requests active exams immediately after publication
- **THEN** the response includes the exam and opening time
- **AND** the start action remains unavailable until `available_from`

#### Scenario: Candidate attempts to start before opening
- **GIVEN** the candidate has a valid scope but the current time is before `available_from`
- **WHEN** the candidate calls the start API
- **THEN** the system rejects the start without creating an attempt

#### Scenario: Candidate already submitted without retake grant
- **GIVEN** a candidate has submitted an exam and has no unused retake grant
- **WHEN** the candidate requests active exams
- **THEN** the submitted exam is excluded from the active exam list according to the existing active-exam response contract

### Requirement: Practice API Privacy
The system MUST require `X-Candidate-Token` from an active account for practice APIs and MUST use the same shared active question bank that formal exams draw from. Practice question responses MUST omit correct answers and analysis before submission. After an authenticated candidate submits one answer, the response SHALL reveal that submission's correctness, normalized correct answer, analysis, and selected-versus-correct option comparison; each submission MUST remain immutable.

#### Scenario: Candidate lists practice questions
- **GIVEN** a valid candidate token for an active account
- **WHEN** the candidate requests practice questions
- **THEN** the response draws from the shared active question bank
- **AND** it omits correct answers and analysis

#### Scenario: Candidate submits practice answer
- **GIVEN** a valid candidate token and an active practice question from the shared bank
- **WHEN** the candidate submits a practice answer
- **THEN** the system persists one immutable practice result
- **AND** the response returns correctness, the normalized correct answer, analysis, and option comparison

#### Scenario: Candidate changes an already submitted practice answer
- **GIVEN** a practice result has already been returned for one submission
- **WHEN** the candidate answers that question again
- **THEN** the system creates a new practice-answer record rather than modifying the prior result

## ADDED Requirements

### Requirement: Active Account Candidate API Authorization
Every candidate-facing API MUST validate both the signed `X-Candidate-Token` and the account's current status as `active` at request time. This check MUST cover exam discovery, start, resume, attempt read, answer save, submit, takeover, result, practice, wrong-question, learning, and account-profile APIs; token issuance-time status alone is insufficient. Candidate tokens MUST expire no later than four hours and MUST be rejected after the existing guarded close-exam invalidation boundary.

#### Scenario: Inactive account calls an attempt API
- **GIVEN** an account was active when its token was issued but is now `inactive`
- **WHEN** it calls attempt read, answer save, submit, resume, or takeover
- **THEN** the API rejects the request before reading or mutating attempt state

#### Scenario: Active account calls candidate APIs
- **GIVEN** a valid unexpired candidate token and a currently `active` account
- **WHEN** the account calls a candidate API outside any other business restriction
- **THEN** the request passes the account-status gate and proceeds to endpoint-specific authorization

#### Scenario: Candidate token exceeds its session boundary
- **WHEN** a candidate token is older than four hours or was signed before the latest guarded close-exam invalidation
- **THEN** every candidate-facing API rejects it
- **AND** the frontend clears the local candidate session

### Requirement: Formal Exam Scope Authorization
Formal exam authorization MUST be scope-only. An active account MAY discover, start, resume, read attempts, and read results for an exam only when a matching immutable `exam_candidate_scope` row exists for that account and exam. Email delivery, invitation-link possession, practice access, display-name changes, or a previously valid token MUST NOT grant formal scope, and publication MUST freeze the scoped roster.

#### Scenario: Unscoped active account requests a formal exam
- **GIVEN** an active account has no `exam_candidate_scope` row for a published exam
- **WHEN** it requests discovery, start, resume, attempt, or result data for that exam
- **THEN** the system rejects or omits the exam
- **AND** it does not create or expose formal attempt state

#### Scenario: Scoped account uses an invitation link
- **GIVEN** an account has a matching frozen exam scope and follows an invitation link through login or registration
- **WHEN** the account completes authentication
- **THEN** the link preserves the target exam for navigation
- **AND** authorization still comes only from the frozen scope row, not from the link itself

#### Scenario: Practice access is not formal scope
- **GIVEN** an active account may practice from the shared question bank
- **WHEN** it has no scope for a formal exam
- **THEN** practice remains available subject to the active-account gate
- **AND** formal exam discovery and attempt APIs remain denied

### Requirement: Wrong-Question Review
The system SHALL provide each authenticated active account with a wrong-question review derived only from that account's immutable practice history over the shared question bank. Review results MUST support the existing category filtering and mastered-state behavior without exposing another account's history.

#### Scenario: Candidate reviews incorrect practice
- **GIVEN** an active account has an incorrect practice submission
- **WHEN** the candidate opens wrong-question review
- **THEN** the system lists the corresponding shared-bank question and supports category filtering
- **AND** it does not expose another account's practice history

#### Scenario: Candidate later answers correctly
- **GIVEN** an earlier incorrect practice submission exists
- **WHEN** a later practice submission for the same question is correct
- **THEN** the item is shown as mastered in the current review state
- **AND** the earlier incorrect history remains persisted

## REMOVED Requirements

### Requirement: Sentinel Candidate for Unknown Identities
The sentinel-candidate login contract is removed. Unknown, ambiguous, inactive, and missing-email identity outcomes MUST NOT create or use a designated sentinel row; valid new emails follow the normal OTP delivery and registration-completion path instead.

#### Scenario: Unknown valid email bypasses the sentinel
- **WHEN** a user requests an OTP for a valid email that has no account
- **THEN** the system sends the OTP to that email and records no sentinel challenge

### Requirement: Audit Log for Unknown-Identity Login Attempts
The unknown-identity audit contract is removed because email-only challenges no longer classify valid mailboxes as roster misses. Delivery and security events continue to follow the redacted operational logging rules in the modified login requirement.

#### Scenario: New valid email is not logged as a roster miss
- **WHEN** a valid new email requests an OTP
- **THEN** the event is handled as a normal registration challenge
- **AND** no unknown-roster identity event or sentinel identifier is emitted
