## ADDED Requirements

### Requirement: Product Copy and Terminology Consistency
The system SHALL use synchronized Chinese-English product terminology for visible frontend copy across public, candidate, and admin pages.

#### Scenario: Bilingual page labels render
- **WHEN** a public, candidate, or admin page renders a bilingual eyebrow, section label, compact heading, or table label
- **THEN** the English and Chinese text describe the same canonical product concept from the shared copy contract

#### Scenario: Candidate role terms render
- **WHEN** candidate-facing login, exam list, practice, exam start, exam taking, result, or review pages refer to the current user
- **THEN** the visible copy uses the canonical exam-taker terminology instead of mixing unrelated role labels

#### Scenario: Admin roster terms render
- **WHEN** admin pages refer to exam-scoped participant lists, participant records, roster imports, or roster management actions
- **THEN** the visible copy uses the canonical roster and participant terminology consistently in both Chinese and English labels

#### Scenario: Raw API codes would be visible
- **WHEN** a frontend page or component renders exam status, availability status, attempt status, question type, question status, or report status values received from APIs
- **THEN** the UI maps those values to user-facing display text and MUST NOT expose raw code values such as `draft`, `active`, `archived`, `single`, `multiple`, `judge`, `not_started`, `in_progress`, or `submitted` as ordinary visible copy

#### Scenario: Candidate critical actions render
- **WHEN** the candidate exam workflow renders answer persistence, exam submission, or navigation away from the active exam surface
- **THEN** the labels and feedback consistently distinguish saving answers, submitting the exam, and returning to the exam list

#### Scenario: Admin report and table headers render
- **WHEN** admin report tables, candidate tables, question tables, or responsive mobile table labels render
- **THEN** headers and mobile labels use the same canonical field names and synchronized Chinese-English terminology for equivalent fields

#### Scenario: Page states render
- **WHEN** loading, empty, disabled, or error states render for the same product object or action on related pages
- **THEN** the state copy uses the same canonical object/action names and avoids contradictory terms for the same condition

#### Scenario: Copy contract changes
- **WHEN** reusable product terminology, status labels, or critical action labels are changed
- **THEN** focused frontend tests cover the shared copy helpers or the high-risk visible page labels affected by the change
