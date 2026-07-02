## ADDED Requirements

### Requirement: Import Export Copy Consistency
The system SHALL use the same product terminology in administrator-facing import templates, failure-report workbooks, and download filenames as the admin import UI.

#### Scenario: Administrator downloads import templates
- **GIVEN** an administrator needs import input files
- **WHEN** the administrator downloads question or roster import templates
- **THEN** the generated workbook sheet names and download filenames use the canonical labels `题库导入模板` and `应考名单导入模板`

#### Scenario: Administrator downloads failure report
- **GIVEN** an import batch exists for question, roster, or exam-roster import
- **WHEN** the administrator downloads the failure report workbook
- **THEN** the workbook uses product-facing import type labels, the canonical filename `失败明细.xlsx`, and failure detail headers `ROW · 行号` and `REASON · 原因`

#### Scenario: Import contracts are preserved
- **GIVEN** import export copy changes are applied
- **WHEN** an import template is parsed or an import result is returned through the API
- **THEN** upload template field keys, import result response fields, and stored `import_batch.error_report` JSON keys remain compatible with existing clients
