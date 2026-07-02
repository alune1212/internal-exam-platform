## ADDED Requirements

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
