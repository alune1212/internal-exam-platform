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
