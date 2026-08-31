## MODIFIED Requirements

### Requirement: Bounded Import Validation
The system MUST enforce compressed upload size, ZIP member count, per-member and total uncompressed size, compression ratio, worksheet count, and row count limits before persisting valid import rows. ZIP structure and expansion limits MUST be evaluated before the workbook parser expands XML content.

#### Scenario: Import file exceeds configured limits
- **GIVEN** an import file exceeds the configured upload, ZIP expansion, row, or worksheet limits
- **WHEN** the administrator submits the import
- **THEN** the system rejects the import with the stable limit response before persisting imported rows

#### Scenario: XLSX archive exceeds expansion limits
- **GIVEN** an uploaded workbook exceeds the configured member, uncompressed-size, or compression-ratio ceiling
- **WHEN** the administrator submits the import
- **THEN** the system rejects it with the stable payload-too-large response before invoking the workbook parser
- **AND** it creates no import batch or imported row

#### Scenario: XLSX archive is malformed or unsafe
- **GIVEN** an upload is not a structurally valid unencrypted XLSX archive, contains duplicate or unsafe paths, or lacks required workbook parts
- **WHEN** the administrator submits the import
- **THEN** the system returns the stable format-validation response before invoking the workbook parser
- **AND** it creates no import batch or imported row

#### Scenario: Import contains mixed valid and invalid rows
- **GIVEN** a structurally safe Excel import within every configured bound contains both valid and invalid rows
- **WHEN** the administrator submits the import
- **THEN** the system persists valid rows and records failed rows with reasons in import-batch metadata
