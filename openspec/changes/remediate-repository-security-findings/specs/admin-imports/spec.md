## MODIFIED Requirements

### Requirement: Bounded Import Validation
The system MUST enforce compressed upload size, ZIP member count, per-member and total uncompressed size, compression ratio, worksheet count, logical worksheet dimensions, and row count limits before persisting valid import rows. ZIP structure and expansion limits MUST be evaluated before the workbook parser expands XML content. A worksheet MUST declare a usable logical dimension, and its logical column dimension MUST NOT exceed 32 columns; either violation MUST be rejected before row iteration.

After ZIP limits pass, the shared preflight MUST reject XML DOCTYPE declarations before openpyxl parses a workbook. This check MUST cover raw-byte encodings and extensionless package parts while allowing ordinary binary members; it MUST NOT rely on filename suffixes or expand XML entities.

#### Scenario: XLSX embeds a DTD in an XML part
- **GIVEN** an otherwise bounded workbook contains a DOCTYPE in any package member, including UTF-16 or an extensionless part
- **WHEN** either supported administrator import receives it
- **THEN** it returns a format error before openpyxl or import persistence

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

#### Scenario: XLSX worksheet has a sparse or inflated logical width
- **GIVEN** an otherwise valid XLSX declares a worksheet dimension wider than 32 columns, including a sparse declaration that does not contain values in the extra columns
- **WHEN** the administrator submits the import
- **THEN** the system returns the stable payload-too-large response before iterating worksheet rows
- **AND** it creates no import batch or imported row

#### Scenario: XLSX worksheet omits its logical dimension
- **GIVEN** an otherwise valid XLSX worksheet omits the logical dimension required to bound streaming reads
- **WHEN** the administrator submits the import
- **THEN** the system returns the stable format-validation response before iterating worksheet rows
- **AND** it creates no import batch or imported row

#### Scenario: Import contains mixed valid and invalid rows
- **GIVEN** a structurally safe Excel import within every configured bound contains both valid and invalid rows
- **WHEN** the administrator submits the import
- **THEN** the system persists valid rows and records failed rows with reasons in import-batch metadata
