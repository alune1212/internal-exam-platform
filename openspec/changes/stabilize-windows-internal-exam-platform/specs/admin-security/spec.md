## MODIFIED Requirements

### Requirement: Admin Session Token
The system SHALL authenticate two named, equal-permission operators with separately configured credentials and protect admin APIs with `X-Admin-Token`. At any moment exactly one operator mode is active: when backup is disabled, only the primary credentials and tokens are valid; when backup is enabled, only the backup credentials and tokens are valid. Enabling backup MUST immediately invalidate the primary credentials and all existing primary tokens; disabling backup MUST immediately invalidate the backup credentials and all existing backup tokens. Formal admin sessions MUST expire after four hours. The backup operator MUST be disabled by default, and the two operators MUST NOT be valid concurrently.

#### Scenario: Primary operator logs in with valid credentials
- **GIVEN** configured primary operator credentials and backup is disabled
- **WHEN** the primary operator submits valid credentials
- **THEN** the system returns a signed four-hour session token carrying the primary operator subject

#### Scenario: Disabled backup operator attempts login
- **GIVEN** configured backup operator credentials and the backup operator is disabled
- **WHEN** those credentials are submitted
- **THEN** the system rejects login without revealing credential details

#### Scenario: Enabled backup operator logs in
- **GIVEN** the local operator workflow enabled the configured backup operator
- **WHEN** the backup operator submits valid credentials
- **THEN** the system returns a signed four-hour session token carrying the backup operator subject
- **AND** the token has the same permissions as the primary operator
- **AND** primary credentials and existing primary tokens are rejected immediately

#### Scenario: Backup operator takes over exclusively
- **GIVEN** backup is disabled and the primary operator may have an active session
- **WHEN** the local operator workflow enables backup
- **THEN** the mode changes atomically to backup-only
- **AND** primary credentials and all existing primary tokens immediately fail authentication
- **AND** only the backup operator can authenticate and call protected admin APIs

#### Scenario: Primary operator resumes exclusively
- **GIVEN** backup is enabled and the backup operator may have an active session
- **WHEN** the local operator workflow disables backup
- **THEN** the mode changes atomically to primary-only
- **AND** backup credentials and all existing backup tokens immediately fail authentication
- **AND** only the primary operator can authenticate and call protected admin APIs

#### Scenario: Concurrent operators are rejected
- **GIVEN** one operator mode is active
- **WHEN** requests present credentials or tokens from both operators as if both were active
- **THEN** the system accepts only the currently active operator mode
- **AND** it never treats the primary and backup operators as simultaneously valid

#### Scenario: Administrator calls protected API without token
- **GIVEN** a protected admin API endpoint
- **WHEN** the request omits a valid `X-Admin-Token`
- **THEN** the system rejects the request

## ADDED Requirements

### Requirement: Loopback-Only Administration
Admin pages, admin APIs, operations status, diagnostics, readiness detail, `/docs`, and `/openapi.json` MUST be reachable only through the Windows loopback operator gateway in the internal deployment.

#### Scenario: LAN client requests an admin surface
- **WHEN** a non-loopback client uses the candidate LAN gateway to request an admin or operational route
- **THEN** the gateway rejects the request before it reaches the backend or admin frontend

#### Scenario: Local operator requests an admin surface
- **GIVEN** the operator is using the dedicated Windows host
- **WHEN** the operator uses the loopback gateway with a valid session
- **THEN** the authorized admin or operations surface is available

### Requirement: Administrative Audit Trail
The system MUST append a non-secret audit event for security-sensitive and state-changing administrator operations. Application APIs MUST NOT allow audit events to be edited or deleted.

#### Scenario: Operator performs a protected action
- **WHEN** an operator logs in, publishes an exam, releases result details, imports data, enables backup access, grants retakes, voids attempts, deletes retained data, or closes sessions
- **THEN** the system records operator subject, action, target, result, allowlisted metadata, request-source hash, and timestamp

#### Scenario: Audit metadata contains sensitive input
- **WHEN** an audited action includes credentials, tokens, OTPs, uploaded files, or unrestricted personal data
- **THEN** those values are excluded from the audit event

#### Scenario: Client attempts to mutate audit history
- **WHEN** a client attempts to update or delete an audit event through the application
- **THEN** no such operation is available or authorized

### Requirement: Guarded Session Revocation
The local close-exam operation MUST revoke every outstanding operator and candidate token only after verifying that no formal attempt remains in progress.

#### Scenario: Session revocation is safe to run
- **GIVEN** no formal attempt is in progress
- **WHEN** the local operator confirms close-exam
- **THEN** a new signing secret is written atomically to protected configuration
- **AND** the backend is recreated and rejects all prior tokens

#### Scenario: Session revocation would interrupt an exam
- **GIVEN** at least one formal attempt is in progress
- **WHEN** close-exam is requested
- **THEN** no secret is rotated and no backend recreation occurs

### Requirement: Operator Secret Isolation
Formal operator credentials and token-signing secrets MUST reside outside the release directory, MUST be protected by Windows filesystem access controls, and MUST NOT be propagated to worker, frontend, evidence, or diagnostic outputs.

#### Scenario: Formal Compose configuration is rendered
- **WHEN** role-scoped environment mappings are inspected
- **THEN** the backend receives the required operator and signing secrets
- **AND** the worker and frontend do not receive them
