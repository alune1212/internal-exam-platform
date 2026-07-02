## ADDED Requirements

### Requirement: Report Export Copy Consistency
The system SHALL use the same product terminology in administrator-facing report workbook sheet names, column headers, and exported status labels as the admin report UI.

#### Scenario: Administrator exports report workbook
- **GIVEN** report data is available for the selected scope
- **WHEN** an administrator downloads the report export workbook
- **THEN** the workbook sheet names use the canonical report labels `个人成绩`, `题目正确率`, `错题排行`, and `参考状态`
- **AND** report column headers use synchronized compact bilingual labels for equivalent fields
- **AND** submitted attendance status is exported as `已交卷` rather than an inconsistent submit label or raw API code

#### Scenario: Report export behavior is preserved
- **GIVEN** report export copy changes are applied
- **WHEN** the administrator requests report export with or without `exam_id`
- **THEN** the system preserves the existing report query scope, workbook structure, and Excel cell escaping behavior
