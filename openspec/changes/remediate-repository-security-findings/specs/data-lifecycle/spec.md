## Purpose

Data lifecycle safeguards ensure that destructive retention operations preserve independently reconstructable historical identity and practice evidence in checksummed, formula-safe archives backed by a later verified paired backup.

## ADDED Requirements

### Requirement: Reconstructable Exam Retention Archive
An exam retention archive used to authorize destructive deletion MUST use schema version 2 and preserve every selected exam's frozen candidate-scope identity, attempt snapshots, and file checksums. The delete operation MUST validate the archive ZIP, inner and outer manifests, member digests, current source identity, preview fingerprint, and a paired backup created after the archive.

#### Scenario: Schema-v2 archive contains frozen roster identity
- **GIVEN** a selected archived exam contains frozen candidate scopes
- **WHEN** the administrator creates its retention archive
- **THEN** JSON and the operator workbook preserve scope and candidate identifiers, frozen email and name, department, position, exam group, and roster remark
- **AND** the archive is sufficient to reconstruct those identities after source deletion

#### Scenario: Legacy or mismatched archive is used for deletion
- **WHEN** an archive is schema version 1, incomplete, checksum-invalid, source-mismatched, or paired with an older or invalid backup
- **THEN** the deletion operation fails without removing source data

### Requirement: Formula-Safe Lifecycle Workbooks
Every lifecycle workbook MUST encode untrusted string values as literal spreadsheet text so that formula-leading and control-character-leading content cannot execute when an operator opens the workbook. Machine-readable JSON MUST retain original values for audit and reconstruction.

#### Scenario: Archived text resembles a spreadsheet formula
- **WHEN** an exam title, roster value, question snapshot, selected answer, correct answer, or practice detail begins with a spreadsheet formula trigger
- **THEN** the XLSX cell is escaped as literal text
- **AND** the corresponding JSON value remains unchanged

### Requirement: Guarded Practice Detail Archive
A practice-detail archive MUST bind exact immutable answer rows, affected aggregate snapshots, retention cutoff, selected accounts, and hot-history policy in a checksummed schema-versioned artifact. Deletion MUST lock affected accounts and revalidate every archived row and the later paired backup before deleting only those identifiers.

#### Scenario: Practice detail archive is created
- **GIVEN** one or more accounts have details older than 365 days or enough detail to exceed the 5000-row hot ceiling
- **WHEN** an administrator archives the eligible rows from a current preview
- **THEN** the resulting ZIP contains exact JSON, formula-safe summary/detail XLSX, and matching manifests and checksums
- **AND** source rows remain unchanged

#### Scenario: Practice archive deletion races with new state
- **WHEN** the preview fingerprint, archived row content, aggregate state, account lock, archive checksum, or paired backup no longer matches
- **THEN** deletion fails closed and leaves every source detail and aggregate unchanged
