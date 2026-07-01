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

### Requirement: Lightweight Internal Boundary
The system SHALL remain a lightweight internal tool unless scope expansion is explicitly approved.

#### Scenario: Change proposes complex access control
- **GIVEN** the first-phase internal-tool boundary is in effect
- **WHEN** a change proposes complex RBAC or multi-tenant authorization
- **THEN** the change is out of scope unless explicitly approved
