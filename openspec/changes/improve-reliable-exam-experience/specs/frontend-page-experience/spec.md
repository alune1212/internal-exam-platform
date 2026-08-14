## MODIFIED Requirements

### Requirement: Frontend Page Query States
The system SHALL distinguish required frontend query loading, empty, recoverable error, and stale-data states on candidate and admin pages, including the invitation target and registration/profile queries. A page MUST NOT turn a pending or failed invitation/account query into an empty exam list or a form with default data.

#### Scenario: Required page query is loading
- **WHEN** a page waits for required query data before it can render meaningful content
- **THEN** the page renders an Academic Editorial loading state using the shared page or table-state primitives

#### Scenario: Required page query fails
- **WHEN** a required candidate or admin page query fails before usable data is available
- **THEN** the page renders an error state instead of showing an empty list, default form data, or an indefinite loading state
- **AND** it offers a scoped retry action or a safe alternative navigation action

#### Scenario: Required page query succeeds with no rows
- **WHEN** a required list or table query succeeds and returns no rows
- **THEN** the page renders an empty state that is visually distinct from loading and error states

#### Scenario: Invitation target query is pending or unavailable
- **WHEN** a login, registration, or exam-list page is resolving an invitation target
- **THEN** the page keeps the return target and renders a loading or error state as appropriate
- **AND** it does not claim that the user has no invitation merely because the query has not completed

#### Scenario: Refresh fails while cached data is available
- **WHEN** a page still has usable data from a previous successful query and a refresh fails
- **THEN** the page keeps the usable content visible
- **AND** it discloses that the update failed, shows the last successful update time when available, and offers retry

#### Scenario: Session is no longer authorized
- **WHEN** a required query fails because the candidate or admin session is invalid or expired
- **THEN** the frontend clears the corresponding local session and returns to the correct login flow
- **AND** it does not present a generic retry loop as if authorization could recover unchanged

### Requirement: Responsive Design Consistency
The system SHALL keep mobile candidate and admin workflows usable without overlap or horizontal overflow, including email login, registration completion, account profile, invitation-aware exam states, and the formal exam focus workspace.

#### Scenario: Candidate focus mode is used on mobile
- **WHEN** the formal exam or practice focus page is viewed on a narrow mobile viewport
- **THEN** fixed bottom navigation does not cover answer controls, question actions, feedback text, or the device safe area
- **AND** formal exam answer-save controls and save status remain available with the same semantics as desktop

#### Scenario: Admin report actions wrap on mobile
- **WHEN** admin report filters, segmented controls, and export actions render on a narrow mobile viewport
- **THEN** the controls wrap within the page header without horizontal overflow

#### Scenario: Registration and invitation pages are used on mobile
- **WHEN** a user completes registration, edits a profile, or opens an invited exam on a narrow viewport
- **THEN** fields, OTP controls, notices, and invitation actions remain reachable and readable
- **AND** no fixed action or responsive table obscures the next required action or introduces horizontal scrolling

#### Scenario: Exam workspace is resized or zoomed
- **WHEN** the exam-taking page is used at 320, 375, or 430 CSS pixels, in mobile landscape, or at 200 percent browser zoom
- **THEN** the active question, options, save state, navigation, and submit action remain reachable without horizontal overflow
- **AND** reduced-motion preferences continue to suppress nonessential motion

## ADDED Requirements

### Requirement: Recoverable Lazy Route Loading
The frontend SHALL replace an unrecoverable lazy-route loading failure with a shared, user-actionable page state. Recovery MUST be initiated by the user and MUST NOT enter an automatic reload loop.

#### Scenario: A route chunk cannot be loaded
- **WHEN** a route module fails to load because its asset is missing, stale, or temporarily unavailable
- **THEN** the page shows a readable resource-loading error with actions to reload the resource or navigate to a safe home
- **AND** it does not leave a blank screen or repeatedly reload without user input

### Requirement: Session-Scoped Exam Draft Recovery
The candidate frontend SHALL write changed answers immediately to the existing tab-scoped draft store and SHALL attempt server synchronization without placing candidate credentials or drafts in durable cross-tab storage. It MUST preserve the server-anchored deadline, revision-conflict rules, and single-submit behavior.

#### Scenario: Candidate changes an answer while online
- **WHEN** a candidate changes an answer in an active attempt
- **THEN** the changed snapshot is written to the tab-scoped draft before the debounced server save
- **AND** the UI announces pending, saving, and saved state without announcing every timer tick

#### Scenario: Browser goes offline and returns online
- **WHEN** the browser reports an offline transition with an unsynchronized draft
- **THEN** the UI immediately reports offline state and retains the draft in the current tab session
- **WHEN** the browser returns online or the page becomes visible again
- **THEN** the frontend retries synchronization in order without creating a duplicate submission

#### Scenario: Candidate backgrounds or reloads the same tab
- **WHEN** an active attempt becomes hidden, receives page-exit notification, or reloads in the same tab session
- **THEN** the latest answer snapshot remains recoverable from the tab-scoped draft
- **AND** the frontend performs a best-effort server save when the browser permits it

#### Scenario: Candidate tries to leave with an unsynchronized draft
- **WHEN** an active attempt has pending, offline, conflict, or error state and the candidate navigates away or closes the page
- **THEN** the frontend presents the applicable unsaved-work warning
- **AND** no warning is presented after the draft is synchronized or the attempt is terminal

#### Scenario: Entire offline tab session is closed
- **WHEN** the browser discards the tab session before an offline draft reaches the server
- **THEN** the system does not claim cross-tab or durable offline recovery
- **AND** candidate credentials remain confined to the existing session-scoped storage boundary

### Requirement: Accessible Exam Focus Navigation
The exam-taking interface SHALL expose question, option, navigation, persistence, conflict, and submission state to keyboard and assistive-technology users without relying only on color or globally intercepting ordinary controls.

#### Scenario: Question and options are announced
- **WHEN** a candidate enters or changes the active question
- **THEN** focus moves to the question heading and announces its number, type, and answered state
- **AND** the option group is labelled by that question heading with selected state exposed semantically

#### Scenario: Candidate uses exam shortcuts
- **WHEN** focus is inside the exam question workspace and not on a button, link, form control, dialog, or sheet
- **THEN** the documented question and answer shortcuts operate
- **AND** those shortcuts do not intercept keyboard interaction with ordinary controls or overlays

#### Scenario: Candidate uses the question navigator
- **WHEN** a candidate focuses a question-navigation item
- **THEN** its accessible name or state identifies whether it is current, answered, or unanswered
- **AND** the same meaning is available without color perception

#### Scenario: Persistence or terminal state changes
- **WHEN** answer persistence becomes offline, saved, conflicted, or failed, or automatic submission occurs
- **THEN** the interface provides a concise live announcement and a recoverable action where applicable
- **AND** repeated countdown updates do not flood the live region

