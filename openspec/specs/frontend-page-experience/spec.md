# Frontend Page Experience Specification

## Purpose

Frontend page experience covers required query states, design-system composition, accessibility semantics, and responsive behavior across candidate and admin pages.

## Requirements

### Requirement: Frontend Page Query States
The system SHALL distinguish required frontend query loading, empty, and error states on candidate and admin pages.

#### Scenario: Required page query is loading
- **WHEN** a page waits for required query data before it can render meaningful content
- **THEN** the page renders an Academic Editorial loading state using the shared page or table-state primitives

#### Scenario: Required page query fails
- **WHEN** a required candidate or admin page query fails before usable data is available
- **THEN** the page renders an error state instead of showing an empty list, default form data, or an indefinite loading state

#### Scenario: Required page query succeeds with no rows
- **WHEN** a required list or table query succeeds and returns no rows
- **THEN** the page renders an empty state that is visually distinct from loading and error states

### Requirement: Data-Dependent Admin Actions
The system MUST NOT expose admin mutation actions that depend on unresolved required query data.

#### Scenario: Administrator opens an exam edit page before the exam record loads
- **WHEN** the exam edit page has not loaded the target exam record
- **THEN** the page does not present editable default exam values or a save action for those defaults

#### Scenario: Administrator opens an exam candidate page before exam state loads
- **WHEN** the exam candidate page has not resolved whether the exam is frozen
- **THEN** the page does not present import, remove, or retake actions as if the exam state were known

### Requirement: Design-System Page Composition
The system SHALL compose ordinary candidate and admin pages from the shared frontend design primitives defined by `frontend/DESIGN.md`.

#### Scenario: Ordinary page renders its main heading
- **WHEN** an ordinary candidate or admin page renders
- **THEN** it uses a single page-level H1 through `PageHeader` or an equivalent heading that follows the documented H1 class contract

#### Scenario: Specialized exam workflow renders
- **WHEN** the formal exam-taking or practice focus workflow renders its active question interface
- **THEN** it may use specialized question, timer, option, and navigator components while preserving shared token, radius, focus, and state conventions

#### Scenario: Local forms and feedback render
- **WHEN** frontend pages render repeated form fields, textareas, alerts, status pills, or feedback notices
- **THEN** they prefer existing local UI, page, and editorial primitives before introducing hand-written styling

### Requirement: Accessible Stateful Controls
The system SHALL expose semantic state and keyboard/focus behavior for custom or segmented frontend controls.

#### Scenario: Segmented filter is selected
- **WHEN** a user changes a segmented filter in candidate results or admin reports
- **THEN** the selected option is exposed through accessible state, not only through visual color

#### Scenario: Custom dropdown is used
- **WHEN** a custom dropdown is used instead of a native select
- **THEN** it provides label association, keyboard operation, focus management, and selected-state semantics

### Requirement: Responsive Design Consistency
The system SHALL keep mobile candidate and admin workflows usable without overlap or horizontal overflow.

#### Scenario: Candidate focus mode is used on mobile
- **WHEN** the formal exam or practice focus page is viewed on a narrow mobile viewport
- **THEN** fixed bottom navigation does not cover answer controls, question actions, or feedback text

#### Scenario: Admin report actions wrap on mobile
- **WHEN** admin report filters, segmented controls, and export actions render on a narrow mobile viewport
- **THEN** the controls wrap within the page header without horizontal overflow
