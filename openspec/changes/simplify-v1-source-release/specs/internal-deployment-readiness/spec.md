## ADDED Requirements

### Requirement: Scoped Source Release
The project SHALL publish v1.0.0 as a versioned source release for the existing controlled-LAN product, preserving all current learning, practice, exam and reporting behavior. Source release evidence MUST identify the exact tested commit separately from the deployed host version. Retired signed-package, Windows and cross-host operational workflows SHALL NOT be required or advertised as supported release paths.

#### Scenario: Source version is released without host upgrade
- **WHEN** the final source candidate passes applicable engineering, browser and capacity checks and is tagged for release
- **THEN** its source archive and release notes identify the tested version and supported Compose build path
- **AND** the existing host is not upgraded or reported as running that version

#### Scenario: Historical operations are retired
- **WHEN** unsupported operational entrypoints and their dedicated checks are removed
- **THEN** shared runtime, migration, security and data-protection checks remain effective
- **AND** historical incomplete acceptance remains incomplete in the retained records

### Requirement: Evidence-Aware Backup Status
The operations snapshot MUST distinguish an absent backup setup from failure to verify existing backup artifacts. Missing evidence MUST NOT imply data recovery is available.

#### Scenario: No backup artifacts exist
- **WHEN** the operator reads status without any backup artifacts
- **THEN** backup status is skipped with an explicit statement that backup or recovery is unverified

#### Scenario: Existing artifacts fail verification
- **WHEN** backup artifacts exist but none can be verified or status cannot be read
- **THEN** backup status is failed and MUST NOT be hidden as an unenabled feature

#### Scenario: Verified backup exists
- **WHEN** backup verification succeeds
- **THEN** its current or stale status and freshness evidence remain visible
