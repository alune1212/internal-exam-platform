# Admin Security Specification

## Purpose

Admin security covers administrator authentication, protected admin APIs, production-safe defaults, and lightweight internal-tool boundaries.

## Requirements

### Requirement: Admin Session Token
The system SHALL authenticate administrators with configured credentials and protect admin APIs with X-Admin-Token.

#### Scenario: Administrator logs in with valid credentials
- **GIVEN** configured administrator credentials
- **WHEN** the administrator submits valid credentials
- **THEN** the system returns a signed session token

#### Scenario: Administrator calls protected API without token
- **GIVEN** a protected admin API endpoint
- **WHEN** the request omits a valid X-Admin-Token
- **THEN** the system rejects the request

### Requirement: Production-Safe Configuration
The system MUST reject unsafe production defaults for administrator password, token secret, and CORS origins.

#### Scenario: Production uses default secret
- **GIVEN** the application runs in production mode
- **WHEN** TOKEN_SECRET or ADMIN_PASSWORD still uses an unsafe default
- **THEN** startup validation rejects the configuration

#### Scenario: Production CORS is unsafe
- **GIVEN** the application runs in production mode
- **WHEN** CORS_ORIGINS contains wildcard, localhost, 127.0.0.1, or 0.0.0.0
- **THEN** startup validation rejects the configuration

### Requirement: Internal-Safe Configuration
The system MUST treat the explicit `internal` runtime profile as a formal-use profile with fail-closed security validation while allowing exact controlled-LAN HTTP origins. It MUST NOT weaken the production profile's HTTPS-only validation.

#### Scenario: Internal profile uses safe formal credentials
- **GIVEN** the backend runs with the internal profile
- **WHEN** administrator credentials, token secret, database credentials, or SMTP delivery use repository sample or unsafe defaults
- **THEN** startup validation rejects the configuration

#### Scenario: Internal profile uses controlled LAN origin
- **GIVEN** the backend runs with the internal profile
- **WHEN** CORS contains one or more exact HTTP origins for the configured private LAN address and contains no wildcard, loopback, localhost, or any-address origin
- **THEN** startup validation accepts the origin boundary

#### Scenario: Internal profile has unsafe network boundary
- **GIVEN** the backend runs with the internal profile
- **WHEN** its LAN bind address is missing, loopback, public, or an any-address value, or CORS is broader than the configured controlled-LAN origin
- **THEN** deployment preflight or startup validation rejects the configuration

#### Scenario: Worker does not require web secrets
- **GIVEN** the auto-submit worker runs with the internal profile and worker role
- **WHEN** role-specific startup validation runs
- **THEN** it validates its database and worker inputs without requiring SMTP or administrator secrets

### Requirement: Lightweight Internal Boundary
The system SHALL remain a lightweight internal tool unless scope expansion is explicitly approved.

#### Scenario: Change proposes complex access control
- **GIVEN** the first-phase internal-tool boundary is in effect
- **WHEN** a change proposes complex RBAC or multi-tenant authorization
- **THEN** the change is out of scope unless explicitly approved
