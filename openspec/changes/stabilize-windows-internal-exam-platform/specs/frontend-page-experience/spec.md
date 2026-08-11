## ADDED Requirements

### Requirement: Supported Browser Self-Check
The candidate frontend SHALL support current stable Edge and Chrome on Windows, current stable Chrome on Android, and the current major Safari on iOS. It MUST warn users of unsupported legacy or embedded in-app browsers before they begin a formal attempt.

#### Scenario: Supported browser opens candidate login
- **WHEN** a supported browser opens the candidate platform
- **THEN** the page permits the normal login and device-check flow

#### Scenario: Unsupported browser opens candidate login
- **WHEN** a detected legacy or embedded in-app browser opens the platform
- **THEN** the page displays an explicit instruction to use a supported browser
- **AND** does not present the unsupported environment as exam-ready

### Requirement: Explicit Answer Synchronization State
The formal exam page MUST distinguish pending, saving, saved, offline, conflict, and failed answer states and MUST keep the retry or takeover action accessible on desktop and mobile.

#### Scenario: Answer save succeeds
- **WHEN** the server accepts the current answer revision
- **THEN** the page displays saved state and the server save time or equivalent confirmation

#### Scenario: Network becomes unavailable
- **WHEN** an answer cannot reach the server because connectivity is unavailable
- **THEN** the page displays offline or pending-sync state
- **AND** retains the local session draft for later retry

#### Scenario: Another device owns the attempt
- **WHEN** save or submit receives an attempt-session conflict
- **THEN** the page stops automatic overwrite attempts
- **AND** explains that the candidate must continue on the active device or complete explicit takeover after a new OTP login

### Requirement: Session-Scoped Draft Recovery
The exam frontend MUST persist pending selections only in session-scoped storage keyed by candidate, attempt, attempt-session generation, and answer revision. It MUST clear matching draft data after successful submission or session invalidation.

#### Scenario: Candidate reloads after a transient failure
- **GIVEN** a matching local draft exists for the current attempt session
- **WHEN** the attempt page reloads
- **THEN** the page restores the pending selections without showing them as server-saved
- **AND** retries synchronization when possible

#### Scenario: Candidate closes or submits the session
- **WHEN** submission succeeds or the candidate session is invalidated
- **THEN** matching local draft and attempt-session values are removed

### Requirement: Third-Party-Free Runtime Assets
The built frontend MUST make no runtime request to third-party font, script, style, CDN, analytics, or asset origins. Required assets and their licenses MUST ship with the release or use the documented system stack.

#### Scenario: Candidate and admin pages load without Internet access
- **WHEN** the Windows host and client browsers can reach the internal platform but not the public Internet
- **THEN** all page layout, fonts or fallbacks, icons, scripts, styles, and exam interactions remain usable
- **AND** Content Security Policy permits only required same-origin runtime resources

### Requirement: Lightweight Accessibility Release Gate
Representative candidate and admin flows MUST pass automated and manual checks for semantic labels, keyboard and focus operation, visible state, contrast, error announcement, responsive zoom, and non-overlapping mobile controls.

#### Scenario: Accessibility gate detects a blocking regression
- **WHEN** a required control lacks an accessible name, keyboard path, visible focus, or usable mobile layout
- **THEN** the frontend release gate fails until the regression is corrected or explicitly removed from the supported flow

### Requirement: Core Browser End-To-End Gate
The release MUST run browser E2E through the real Nginx, backend, and PostgreSQL stack for local admin login/publication, OTP candidate login, start, revisioned save, reload recovery, submit, result visibility/release, single-device conflict, and close-exam session invalidation.

#### Scenario: Core browser flow passes
- **WHEN** the E2E suite executes against the disposable Windows project
- **THEN** every required flow completes without console error, unhandled request failure, blank state, or cross-surface route exposure

#### Scenario: Core browser flow fails
- **WHEN** any required E2E assertion fails
- **THEN** the release is not eligible for formal promotion

### Requirement: Local Operations Page States
The loopback-only operations page MUST distinguish loading, current, degraded, stale, skipped, and failed values for version, migration, health, worker, backup, storage, retention, and security signals.

#### Scenario: Operations query partially fails
- **WHEN** one operational signal cannot be loaded while others remain available
- **THEN** the page identifies the failed signal without collapsing the entire view to healthy, zero, or empty state

### Requirement: Behavior-Preserving Exam UI Decomposition
Refactoring the exam-taking frontend MUST preserve its public routes, Academic Editorial tokens and primitives, snapshot rendering, question navigation, server-derived countdown, save-before-submit ordering, and mobile/desktop behavior except for the explicitly added attempt-session and draft-recovery contracts.

#### Scenario: Refactored exam page runs regression tests
- **WHEN** existing and new exam-taking tests execute after decomposition
- **THEN** unchanged behaviors remain equivalent and the new synchronization behaviors pass
