## ADDED Requirements

### Requirement: Fail-Closed Security Scan Severity
Release security evaluation MUST normalize only the documented scanner severity vocabulary and MUST fail closed on empty, malformed, non-string, or unknown explicit severity values. A pip-audit finding without severity MUST retain the documented conservative high default.

#### Scenario: Scanner emits a supported severity variant
- **WHEN** a supported severity differs only by case or surrounding whitespace, or npm emits `moderate`
- **THEN** the evaluator maps it to the canonical policy severity before applying release policy

#### Scenario: Scanner emits an unsupported severity
- **WHEN** a scanner finding contains an empty, malformed, non-string, or unknown explicit severity
- **THEN** evaluation fails with a security-input error
- **AND** the release cannot receive a passing security record

### Requirement: Authenticated macOS Release Bundle
A sealed macOS release MUST carry detached RSA-3072 SHA-256 signatures over the final manifest and checksum file. Every install, start, promotion, rollback, or preflight path MUST verify those signatures against an owner-controlled public key and pinned fingerprint outside the release bundle before trusting or executing bundle content.

#### Scenario: Signed release is valid
- **GIVEN** a sealed release has both exact signature sidecars and its external public key fingerprint matches the signed manifest
- **WHEN** the trusted verifier checks signatures, manifest, checksums, and payload
- **THEN** the release may proceed to the next formal operation

#### Scenario: Release authenticity is missing or altered
- **WHEN** a signature, manifest, checksum, payload, public key, or fingerprint is missing, replaced, mismatched, or accompanied by an unlisted signature file or symlink
- **THEN** verification fails before any bundle script, Docker action, installation, promotion, or rollback is executed

### Requirement: Trusted Forwarded Client Identity
The deployment MUST overwrite client-supplied forwarded-address headers at both Nginx gateways and MUST configure the backend to trust forwarding metadata only from the two exact static gateway peers on a dedicated non-overlapping network.

#### Scenario: Client supplies a forged forwarded address
- **WHEN** a client sends a forged or rotating `X-Forwarded-For` value through either supported gateway
- **THEN** Nginx replaces it with the actual peer address
- **AND** application rate limits and audit hashing use the stable real client identity

#### Scenario: Proxy topology is unsafe or ambiguous
- **WHEN** the gateway subnet overlaps another active network, static gateway addresses are missing or inconsistent, the forwarding allowlist is wildcard/broad, or the backend is published directly
- **THEN** deployment configuration or formal preflight fails closed

### Requirement: Isolated Pull-Request Browser Gate
The pull-request browser gate MUST orchestrate disposable services from the trusted job context and MUST NOT expose the host Docker socket or Docker client to PR-controlled browser code. Its job token MUST be read-only and checkout credentials MUST NOT persist in the workspace. Every `actions/checkout` step in the pull-request workflow MUST explicitly set `persist-credentials: false`.

#### Scenario: Browser tests execute pull-request code
- **WHEN** the browser E2E job builds and runs a pull-request checkout
- **THEN** the browser container has only the fixed candidate/operator network endpoints and artifact directory it needs
- **AND** it has no Docker socket, Docker CLI, privileged mode, or persisted checkout credential

#### Scenario: Any pull-request job checks out source
- **WHEN** a pull-request workflow job checks out repository source
- **THEN** the job uses a read-only `contents: read` workflow token
- **AND** that checkout explicitly disables credential persistence

### Requirement: Recoverable Backup Freeze
Backup operations MUST release an owned backup-write freeze after any ordinary exception raised following lock acquisition, while preserving and propagating the original failure. Successful backup, evidence, and audit semantics MUST remain unchanged.

#### Scenario: Post-acquisition backup work fails
- **GIVEN** a backup operation has acquired the write freeze
- **WHEN** fingerprinting, backup creation, verification, pruning, or evidence finalization raises an ordinary exception
- **THEN** the operation releases its owned freeze before returning the failure
- **AND** it propagates the original exception without leaving a stranded lock

### Requirement: Recomputed Release Scanner Evidence
A macOS release security report MUST be bound to an exact retained set of raw pip-audit, npm-audit, Trivy, disposition, and image-identity inputs. Trusted sealing and bundle verification MUST recompute the canonical scanner-evidence digest from those inputs and fail closed on missing, extra, linked, malformed, tampered, or mismatched evidence.

#### Scenario: Caller supplies a self-authored passing report
- **WHEN** a caller provides a `passed` report and matching checksum sidecar without the exact raw evidence that recomputes to its claimed digest
- **THEN** sealing fails before the report enters the release or receives an offline signature

#### Scenario: Signed bundle contains retained scanner evidence
- **WHEN** Test, Install, Start, Promote, or Rollback verifies a signed release
- **THEN** trusted code validates exact raw-evidence membership and recomputes the report binding before trusting the release

### Requirement: Single Guarded Paired-Backup Entry Point
Every paired database and media backup MUST acquire the shared write freeze through the guarded `run_paired_backup`/`container-backup` path before reading or dumping mutable data. An unfrozen legacy backup command or documented implementation MUST not remain callable.

#### Scenario: Legacy backup command is invoked
- **WHEN** an operator invokes the retired legacy paired-backup command
- **THEN** the command is absent or fails before starting `pg_dump` or media archiving
- **AND** the guarded backup path remains the only path that can create a paired backup

#### Scenario: Guarded paired backup runs
- **WHEN** an operator invokes the supported paired-backup operation
- **THEN** the write freeze is acquired before database or media reads and released on success or failure

### Requirement: External Trust Before Bundled macOS Code
Bundled macOS Test, Install, Start, Promote, Rollback, and LaunchAgent-dispatcher entrypoints MUST validate the external owner-controlled runtime, exact release identity, public key, and required signatures before sourcing any bundle-controlled script. Caller-set environment markers MUST never establish trust.

#### Scenario: Caller forges lifecycle trust markers
- **WHEN** a caller sets environment variables that claim an unverified release is trusted
- **THEN** the entrypoint fails before sourcing bundled common or lifecycle code
- **AND** no bundle-controlled command executes

#### Scenario: Trusted release enters a lifecycle operation
- **GIVEN** the external runtime and exact release have passed signature and fingerprint verification
- **WHEN** a supported lifecycle entrypoint runs
- **THEN** it may source the verified bundle code and continue its normal operation

### Requirement: Fail-Closed First Formal Writer Commissioning
A fresh protected macOS root MUST provide one trusted-checkout generation-1 commissioning entrypoint. Preparation MUST create only checksummed pending identity, current-release, and fresh-volume state. Activation MUST retain the private pending barrier until it has validated and bound the exact signed release, canonical staging acceptance, paired backup, restore drill, formal preflight, browser smoke, privileged host evidence, and writer fence; only then MAY it create immutable terminal/lineage evidence and make public start ready.

#### Scenario: Fresh root is prepared
- **GIVEN** an installed signed release and an empty protected root with explicit empty-dataset approval
- **WHEN** the designated operator prepares the first writer from the matching clean trusted checkout
- **THEN** generation 1 is reserved with fresh volumes and `bootstrapPending=true`
- **AND** public start remains blocked

#### Scenario: Activation evidence is incomplete or valid
- **WHEN** any required artifact, checksum, release/host identity, freshness check, or writer-fence binding is absent or mismatched
- **THEN** activation fails closed and the writer remains private and resumable
- **WHEN** every required artifact and binding is valid
- **THEN** checksummed activation intent, terminal, phase, and immutable lineage records are created
- **AND** the exact generation-1 current state becomes public-ready without accepting a handwritten state shortcut

### Requirement: Explicit Protected Staging Configuration
The macOS host workflow MUST generate the owner-only staging environment from the protected formal configuration and replace its runtime-specific values with fixed disposable loopback ports, a dedicated gateway network, and a distinct random canonical `TOKEN_SECRET`. The snapshot MUST explicitly enable the disposable migration acknowledgements and real SMTP delivery, MUST disable any fixed test OTP, and MUST reject missing fields, missing formal signing keys, shared formal/staging signing keys, or conflicting caller environment overrides before any staging Docker command executes. Both files MUST use unique canonical `NAME=value` assignments, and signing keys MUST be unquoted canonical values, so alternate dotenv syntax or duplicate keys cannot change the effective Compose signing key after validation.

#### Scenario: Staging configuration is absent or inherited
- **WHEN** `staging.env` is empty, incomplete, linked, uses in-memory delivery, contains a fixed test OTP, or is overridden by conflicting shell values
- **THEN** every staging entrypoint fails before rendering or starting Compose

#### Scenario: Formal configuration is synchronized for staging
- **GIVEN** the protected formal configuration contains the required credentials and SMTP settings
- **WHEN** the designated operator explicitly synchronizes staging configuration
- **THEN** required configuration is copied and a fresh independent staging signing key is generated without printing secrets
- **AND** formal keys and sessions remain unchanged while prior staging tokens become invalid
- **AND** the result uses the fixed loopback ports, disposable database acknowledgements, real SMTP, and the dedicated non-overlapping staging gateway network

#### Scenario: Staging reuses the formal signing key
- **WHEN** a staging environment contains the same `TOKEN_SECRET` as formal, the formal key is missing, or quoting, duplicate keys, or alternate assignment syntax makes the effective signing key ambiguous
- **THEN** staging validation fails before Docker
- **AND** correctly isolated staging candidate, admin, and playback tokens cannot authenticate against the formal key even when their subjects match
