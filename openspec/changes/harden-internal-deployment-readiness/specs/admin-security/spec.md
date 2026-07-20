## ADDED Requirements

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
