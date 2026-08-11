## ADDED Requirements

### Requirement: Selected macOS Host Acceptance Gate
The system SHALL define a formal internal-release gate that requires automated quality and security checks, healthy services, real SMTP delivery, business UAT, worker and Docker recovery, verified paired-backup restoration, an independent encrypted second copy on a distinct physical device or host, split-route verification, approved-CIDR/pf (or managed equivalent) port negative tests, explicitly disabled Docker Desktop Resource Saver on macOS, mandatory Mac formal LaunchAgent load/status/retry/lock evidence when Mac is selected, and host-specific evidence from the selected formal macOS or Windows host. Formal pre-exam, post-exam, pre-upgrade, and cutover backup gates MUST fail closed when the second copy is unavailable or unverified; daily opportunistic backup MAY record skipped/degraded status without claiming formal readiness.

#### Scenario: macOS internal release evidence is complete
- **GIVEN** backend, frontend, OpenSpec, Compose, macOS command, mandatory formal LaunchAgent, dependency, and final-image checks pass
- **AND** native ARM64 staging, backend and worker healthchecks, real OTP delivery, desktop/phone formal exam UAT, Docker/host restart recovery, 100-client capacity, split-route checks, explicitly disabled Resource Saver, and independent encrypted second-copy isolated restore pass on the selected Mac
- **AND** the approved CIDR allows only candidate `8080`, keeps `8081`/`5432`/`5173` loopback-only, leaves backend `8000` and the worker unexposed, and second-device/unapproved-CIDR negative tests pass
- **AND** `launchctl bootstrap`/`print`, bounded Docker-failure retry, and the LaunchAgent execution lock are proven on the real Mac
- **WHEN** release readiness is assessed
- **THEN** that macOS deployment may be marked ready for formal internal use

#### Scenario: Required host evidence is missing
- **GIVEN** any required selected-host healthcheck, security check, SMTP result, UAT, recovery, capacity, split-route, backup, second-copy, restore, or release evidence is missing, stale, borrowed from another host, or failed
- **WHEN** release readiness is assessed
- **THEN** the deployment MUST NOT be marked ready for formal internal use

### Requirement: Cutover Writer Evidence
Formal readiness and host migration evidence MUST identify `datasetId`, `hostId`, and `writerGeneration`. A Mac-to-Windows or Windows-to-Mac target MUST not be exposed until a checksummed `prepare-cutover` manifest proves that the entire source formal project is stopped and `accept-cutover` records the target generation.

#### Scenario: Source project is only partially stopped
- **GIVEN** the source candidate gateway is stopped but another source formal service remains running
- **WHEN** target cutover readiness is assessed
- **THEN** the cutover MUST fail closed and the target MUST NOT accept writes

#### Scenario: Cutover manifest is accepted
- **GIVEN** a valid unconsumed manifest, verified paired backup, isolated target restore, target host evidence, and whole-source-project stop proof
- **WHEN** `accept-cutover` completes
- **THEN** the target becomes the only approved writer for the dataset and generation recorded in the manifest
