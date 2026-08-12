# platform-accounts Specification

## Purpose
Platform accounts provide an email-first identity boundary for learning and invited exams, including OTP registration completion, profile lifecycle, normalized identity, and safe active-session eligibility.
## Requirements
### Requirement: Email-First Account Identity
Every platform account SHALL be identified by one required email address normalized by trimming and case-folding before lookup, persistence, uniqueness checks, or authorization. The normalized email MUST be unique across platform accounts, and account identity MUST NOT depend on a candidate name, employee number, phone suffix, or sentinel row. Email changes and physical account deletion are not available in the first phase.

#### Scenario: New email is normalized and stored
- **WHEN** a valid mailbox completes registration
- **THEN** the account stores the canonical normalized email
- **AND** later lookups with different casing or surrounding whitespace resolve to the same account

#### Scenario: Duplicate normalized email is rejected
- **GIVEN** an account already owns a normalized email
- **WHEN** another registration or import attempts to create a second account for that email
- **THEN** the operation rejects the duplicate without creating a second identity

#### Scenario: Legacy login fields are supplied
- **WHEN** a client submits a name, employee number, phone suffix, or sentinel identifier as login identity
- **THEN** the strict email-only request contract rejects the legacy identity fields
- **AND** email remains the only account-login identifier

### Requirement: New Email Registration Completion
A successful OTP verification for a valid email with no account or with an incomplete `pending` account SHALL produce a short-lived, one-time registration-completion credential rather than a candidate token. An existing `inactive` account MUST not be converted into a new registration through this path; a correct OTP for that mailbox SHALL yield only a stable account-unavailable result until an administrator reactivates the completed account. The credential MUST be scoped only to completing the account profile, MUST be single-use and expiring, and MUST not authorize practice, learning, formal-exam, attempt, or result APIs. The account SHALL remain `pending` until a non-empty display name is confirmed; successful completion SHALL make the account `active` and return a signed candidate token valid for no more than four hours.

#### Scenario: Unknown valid email receives a registration path
- **GIVEN** no account exists for a syntactically valid normalized email
- **WHEN** the email-only OTP challenge is requested and the OTP is verified
- **THEN** the system sends the OTP to that mailbox
- **AND** it returns a one-time registration-completion credential
- **AND** it does not return a candidate token before profile completion

#### Scenario: Registration completion activates the account
- **GIVEN** a pending account and an unexpired unused registration-completion credential
- **WHEN** the user submits a non-empty display name
- **THEN** the credential is consumed
- **AND** the account becomes `active`
- **AND** the response returns a signed four-hour candidate token

#### Scenario: Completion credential is replayed or misused
- **GIVEN** a registration-completion credential is expired, consumed, or presented to a practice or exam endpoint
- **WHEN** the request is processed
- **THEN** the system rejects it
- **AND** it does not issue a candidate token or mutate formal access

#### Scenario: Inactive mailbox proves control
- **GIVEN** a completed account is currently `inactive`
- **WHEN** its owner requests, receives, and correctly verifies a new OTP
- **THEN** verification consumes the challenge and returns the stable account-unavailable outcome
- **AND** it returns neither a registration-completion credential nor a candidate token

### Requirement: Account Display Name
An account SHALL have an independent non-empty display name before it can become `active`. An authenticated active account MAY edit its own display name through the account-profile API, but a display-name edit MUST NOT rewrite immutable published exam-roster identity or historical formal-report identity.

#### Scenario: User completes the required profile
- **GIVEN** a pending account with a valid registration-completion credential
- **WHEN** the user submits a non-empty display name
- **THEN** the display name is persisted on the platform account
- **AND** the account is eligible for active-session token issuance

#### Scenario: Active user edits display name
- **GIVEN** an active account authenticated with its candidate token
- **WHEN** the account owner submits a valid new display name
- **THEN** the platform updates only the account display name
- **AND** it leaves published exam-roster names and historical reports unchanged

#### Scenario: Blank display name is submitted
- **WHEN** registration completion or profile editing receives an empty or whitespace-only display name
- **THEN** the request is rejected
- **AND** the account status and previously stored display name remain unchanged

### Requirement: Account Status Lifecycle
Platform accounts SHALL expose exactly the lifecycle states `pending`, `active`, and `inactive`. A `pending` account lacks completed registration and cannot receive a candidate token, an `active` account may use candidate APIs subject to their scope and attempt checks, and an `inactive` account MUST be denied candidate-token issuance and candidate APIs. Loopback-admin account controls SHALL support searching accounts and activating or deactivating a completed account without changing its normalized email or historical data.

#### Scenario: Pending account is not yet eligible
- **GIVEN** an account has status `pending` and no completed display-name profile
- **WHEN** it presents an OTP or registration credential to a candidate API
- **THEN** the API rejects the request
- **AND** the account remains pending until profile completion

#### Scenario: Operator deactivates an account
- **GIVEN** an active account and an authenticated loopback administrator
- **WHEN** the administrator deactivates the account
- **THEN** its status changes to `inactive`
- **AND** subsequent candidate-token issuance and candidate API calls fail closed

#### Scenario: Operator deactivates an account during an attempt
- **GIVEN** an active account owns an in-progress formal attempt
- **WHEN** the authenticated loopback administrator performs the audited safety deactivation
- **THEN** the status change is allowed even though non-essential formal mutations are gated
- **AND** the next user request is rejected while the attempt and server-side auto-submit eligibility remain intact

#### Scenario: Operator searches the account directory
- **GIVEN** an authenticated loopback administrator
- **WHEN** the administrator searches by normalized email, display name, or lifecycle status
- **THEN** the system returns a bounded account-directory result with `pending`, `active`, or `inactive` state
- **AND** it exposes no control for email replacement or physical deletion

#### Scenario: Operator reactivates a completed account
- **GIVEN** an inactive account with a completed display name
- **WHEN** the loopback administrator activates it
- **THEN** its status changes to `active`
- **AND** future OTP verification may issue a candidate token subject to the normal four-hour boundary

#### Scenario: Account deletion or email replacement is requested
- **WHEN** a user or administrator requests physical account deletion or a self-service email change
- **THEN** the first-phase API rejects the operation
- **AND** the normalized email and historical account identity remain unchanged

#### Scenario: Migration removes the login sentinel
- **GIVEN** the verified migration identifies the designated system sentinel rather than a real platform account
- **WHEN** the destructive cleanup runs behind its backup and preflight gates
- **THEN** the sentinel may be detached and removed
- **AND** no real `pending`, `active`, or `inactive` account is physically deleted

