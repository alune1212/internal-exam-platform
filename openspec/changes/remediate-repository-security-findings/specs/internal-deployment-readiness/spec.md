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
The pull-request browser gate MUST orchestrate disposable services from the trusted job context and MUST NOT expose the host Docker socket or Docker client to PR-controlled browser code. Its job token MUST be read-only and checkout credentials MUST NOT persist in the workspace.

#### Scenario: Browser tests execute pull-request code
- **WHEN** the browser E2E job builds and runs a pull-request checkout
- **THEN** the browser container has only the fixed candidate/operator network endpoints and artifact directory it needs
- **AND** it has no Docker socket, Docker CLI, privileged mode, or persisted checkout credential

### Requirement: Recomputed Release Scanner Evidence
A macOS release security report MUST be bound to an exact retained set of raw pip-audit, npm-audit, Trivy, disposition, and image-identity inputs. Trusted sealing and bundle verification MUST recompute the canonical scanner-evidence digest from those inputs and fail closed on missing, extra, linked, malformed, tampered, or mismatched evidence.

#### Scenario: Caller supplies a self-authored passing report
- **WHEN** a caller provides a `passed` report and matching checksum sidecar without the exact raw evidence that recomputes to its claimed digest
- **THEN** sealing fails before the report enters the release or receives an offline signature

#### Scenario: Signed bundle contains retained scanner evidence
- **WHEN** Test, Install, Start, Promote, or Rollback verifies a signed release
- **THEN** trusted code validates exact raw-evidence membership and recomputes the report binding before trusting the release
