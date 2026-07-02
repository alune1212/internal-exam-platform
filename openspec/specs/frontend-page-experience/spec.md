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

### Requirement: Admin Brand Mark Consistency
The system SHALL use a consistent brand glyph for the browser tab identity and repeated admin chrome wordmarks while preserving readable light and dark variants.

#### Scenario: Admin chrome renders brand identity
- **WHEN** an authenticated administrator views the desktop side rail, mobile admin header, or shared footer
- **THEN** the visible wordmark uses the same brand glyph shape as the browser tab icon, with colors adapted to the current surface

#### Scenario: Brand text remains available
- **WHEN** the brand wordmark renders in admin chrome
- **THEN** the product label and optional subtitle remain visible or accessible according to the existing wordmark pattern

### Requirement: Viewport-Stable Admin Side Rail
The system SHALL keep desktop admin side rail navigation and logout positioned within the viewport instead of allowing long page content to push logout to the document bottom.

#### Scenario: Long admin page is viewed on desktop
- **WHEN** an administrator opens a long admin page such as the question list
- **THEN** the desktop side rail remains viewport-stable and the logout action stays near the bottom of the visible rail

#### Scenario: Mobile admin menu is used
- **WHEN** an administrator opens the mobile admin navigation sheet
- **THEN** the navigation items and logout action remain reachable without horizontal overflow

### Requirement: Product-Styled Import File Picker
The system SHALL present admin import file selection through product-styled controls that use shared UI primitives instead of exposing the browser-default file input as the primary visible control.

#### Scenario: Administrator selects an Excel file
- **WHEN** an administrator activates the visible file-selection control on a question or candidate import page and chooses an Excel file
- **THEN** the page shows the selected filename and enables the existing upload action for that file

#### Scenario: Administrator has not selected a file
- **WHEN** an administrator views a question or candidate import page before selecting a file
- **THEN** the upload action remains disabled and the file picker communicates that no file is selected

#### Scenario: Keyboard user selects a file
- **WHEN** a keyboard user focuses and activates the import file picker
- **THEN** the control remains operable through native file input semantics and visible focus styling

#### Scenario: Import behavior is preserved
- **WHEN** an administrator uploads a selected file from a question or candidate import page
- **THEN** the page uses the existing import API behavior, success/error notices, query invalidation, and failure-report download behavior for that page
