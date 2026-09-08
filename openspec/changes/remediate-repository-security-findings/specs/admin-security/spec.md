## MODIFIED Requirements

### Requirement: Production-Safe Configuration
The system MUST reject unsafe formal defaults and runtime values for the effective administrator credentials, database credentials, session signing secret, administrator and candidate session lifetimes, and CORS origins. Formal backend configuration MUST use a canonical unpadded Base64url `TOKEN_SECRET` that decodes to exactly 32 bytes, and both formal session lifetimes MUST equal four hours. Formal worker configuration MUST validate its database credential without receiving unrelated web secrets.

#### Scenario: Production uses default secret
- **GIVEN** the application runs in production mode
- **WHEN** the effective operator password, database password, or `TOKEN_SECRET` uses a missing, sample, or noncanonical value
- **THEN** startup validation rejects the configuration without printing secret material

#### Scenario: Formal backend uses missing or sample operator credentials
- **GIVEN** the backend runs with the internal or production profile
- **WHEN** the effective operator username or password is blank, whitespace-only, or a repository sample value
- **THEN** startup validation rejects the configuration without printing the credential

#### Scenario: Formal role uses unsafe database credentials
- **GIVEN** a backend or worker runs with the internal or production profile
- **WHEN** the configured database password is blank or a repository sample value
- **THEN** startup validation rejects the configuration without printing the connection string

#### Scenario: Formal backend uses noncanonical signing material
- **GIVEN** the backend runs with the internal or production profile
- **WHEN** `TOKEN_SECRET` is not the canonical unpadded Base64url encoding of exactly 32 bytes
- **THEN** startup validation rejects the configuration without printing the secret

#### Scenario: Formal session lifetime differs from four hours
- **GIVEN** the backend runs with the internal or production profile
- **WHEN** the administrator or candidate session lifetime is not exactly 14400 seconds
- **THEN** startup validation rejects the configuration

#### Scenario: Production CORS is unsafe
- **GIVEN** the application runs in production mode
- **WHEN** CORS origins contain a wildcard, loopback, localhost, any-address, or non-HTTPS origin
- **THEN** startup validation rejects the configuration

## ADDED Requirements

### Requirement: Signed Token Field Validation
The system MUST treat malformed signed-token subjects and timestamps as invalid authentication rather than unhandled application errors. Numeric fields MUST use bounded ASCII decimal syntax and candidate identifiers MUST fit the positive database identifier range.

#### Scenario: Token contains an alternate or oversized numeric representation
- **WHEN** an administrator or candidate token contains Unicode digits, an oversized timestamp, or an out-of-range candidate identifier
- **THEN** the protected API rejects the token with the normal unauthorized response
- **AND** no unhandled conversion error reaches the application error handler

### Requirement: Tab-Scoped Browser Credentials
Administrator tokens, candidate sessions, attempt-session credentials, and attempt drafts MUST be restored only from the current tab's session storage. The application MUST remove known legacy persistent keys without reading or promoting their values and MUST preserve unrelated browser storage.

#### Scenario: Browser contains legacy persistent credentials
- **GIVEN** a browser has a legacy administrator, candidate, attempt-session, registration, or attempt-draft key in persistent local storage
- **WHEN** the current application starts, logs out, or handles an unauthorized response
- **THEN** it removes only the known project keys
- **AND** it does not authenticate or restore an attempt from those values

### Requirement: Fail-Closed Destructive Account Migration
The destructive account migration MUST require an explicit recognized environment before any schema or data mutation. Formal environments MUST satisfy the complete maintenance gate, while a development bypass MUST require explicit disposable acknowledgements and a constrained development or test database target.

#### Scenario: Migration environment is absent or unknown
- **WHEN** the destructive migration starts without a recognized explicit environment
- **THEN** it fails before executing any DDL or destructive data mutation

#### Scenario: Formal migration lacks maintenance evidence
- **GIVEN** the environment is internal, production, or the supported formal compatibility value
- **WHEN** writer fencing, paired backup, independent copy, restore-drill, or no-active-attempt evidence is missing
- **THEN** the migration fails closed regardless of a false gate flag

#### Scenario: Disposable development migration is explicit
- **GIVEN** the environment is development and the target is a constrained development or test PostgreSQL database
- **WHEN** both documented disposable-development acknowledgements are true
- **THEN** the migration may use the development path without formal external evidence

### Requirement: Exact Disposable PostgreSQL Test Target
Any automated test that drops schemas or truncates PostgreSQL data MUST verify an explicit disposable marker, the expected PostgreSQL driver, a loopback host, the exact test database and user, and an explicitly matching port before it connects or mutates data.

#### Scenario: Destructive PostgreSQL test target is ambiguous
- **WHEN** any required target attribute is missing or differs from the documented disposable test identity
- **THEN** the test aborts before opening a destructive connection
- **AND** the error does not expose the password or complete connection string

### Requirement: Bounded Public Rate-Limit Rejection State
The shared public-token rate limiter MUST enforce its configured maximum key count before recording rejected requests, so unique unauthenticated verification identifiers cannot bypass eviction. Accepted and rejected requests MUST both retain only bounded limiter state.

#### Scenario: Unique rejected identifiers exhaust a source quota
- **GIVEN** one source has reached its public-token quota and the limiter has a configured key cap
- **WHEN** the source submits many unique challenge or verification identifiers that are rejected
- **THEN** the limiter returns the normal rate-limit response
- **AND** retained limiter buckets never exceed the configured key cap
