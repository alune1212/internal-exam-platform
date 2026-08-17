# Frontend Page Experience Specification

## Purpose

Frontend page experience covers required query states, design-system composition, accessibility semantics, and responsive behavior across candidate and admin pages.
## Requirements
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

### Requirement: Data-Dependent Admin Actions
The system MUST NOT expose admin mutation actions that depend on unresolved required query data.

#### Scenario: Administrator opens an exam edit page before the exam record loads
- **WHEN** the exam edit page has not loaded the target exam record
- **THEN** the page does not present editable default exam values or a save action for those defaults

#### Scenario: Administrator opens an exam candidate page before exam state loads
- **WHEN** the exam candidate page has not resolved whether the exam is frozen
- **THEN** the page does not present import, remove, or retake actions as if the exam state were known

### Requirement: Design-System Page Composition
The system SHALL compose every current frontend route from the canonical design contract defined by `frontend/DESIGN.md`. The presentation SHALL retain the warm-paper palette, restrained Academic Editorial tone, and offline-safe system-font stacks while allowing navigation presentation, typography hierarchy, page skeletons, and result composition to be redesigned. Ordinary pages MUST use shared owners for page width, surfaces, fields, status feedback, data presentation, and actions while preserving four explicit composition contexts: Candidate Calm, Admin Workbench, Exam Focus, and the chrome-free Auth Canvas. These composition rules MUST NOT change route paths, navigation destinations, authorization, API contracts, or exam-delivery semantics.

#### Scenario: Ordinary page renders its main heading
- **WHEN** an ordinary candidate or admin page renders
- **THEN** it uses one page-level H1 whose Chinese task name is the primary visible label
- **AND** any context label is optional, meaningful, upright, and visually subordinate to the H1

#### Scenario: Ordinary candidate page renders
- **WHEN** a candidate opens an ordinary learning, practice-entry, exam-list, result, review, or profile page
- **THEN** the page uses Candidate Calm composition with calm density, clear task hierarchy, and the existing candidate navigation destinations
- **AND** it does not render the admin workbench navigation or the active-attempt navigator

#### Scenario: Ordinary admin page renders
- **WHEN** an administrator opens a dashboard, list, import, edit, workspace, operations, or report page
- **THEN** the page uses Admin Workbench composition with compact scan-friendly density and the existing admin navigation destinations
- **AND** it does not use candidate navigation, a marketing hero, or candidate-page spacing as its default

#### Scenario: Specialized exam workflow renders
- **WHEN** the formal exam-taking or practice focus workflow renders its active question interface
- **THEN** it uses Exam Focus composition with task-relevant question, timer, persistence, navigation, and submission controls
- **AND** unrelated ordinary-page navigation or heading chrome does not compete with the active attempt

#### Scenario: Authentication canvas renders
- **WHEN** a login, registration, or registration-completion route renders before the application shell is available
- **THEN** it uses a minimal Auth Canvas without candidate navigation, admin navigation, or a decorative global footer
- **AND** its identity step, validation, recovery, and primary action use the shared form and feedback contracts

#### Scenario: Repeated page pattern renders
- **WHEN** a current route needs a page frame, bounded surface, field, status treatment, action group, report toolbar, or responsive data region
- **THEN** it uses the documented shared pattern or an explicitly governed family-specific variant
- **AND** the page does not recreate the same visual contract from local width, border, radius, shadow, typography, and spacing rules

#### Scenario: Local forms and feedback render
- **WHEN** frontend pages render repeated fields, textareas, selects, alerts, status pills, or feedback notices
- **THEN** they use the shared field, control, status, and feedback contracts before introducing a local presentation variant

#### Scenario: Login, registration, and profile pages render
- **WHEN** an email login, first-registration profile, admin login, or account-profile page renders
- **THEN** its fields, actions, notices, and validation feedback use the shared Auth or Candidate form and feedback contracts
- **AND** the presentation change does not alter identity, registration, session, or profile behavior

### Requirement: Accessible Stateful Controls
The system SHALL expose semantic state and complete keyboard/focus behavior for native, custom, segmented, file-selection, question-option, dialog, and sheet controls. Repeated controls SHALL provide documented default, hover, focus-visible, active or selected, disabled, pending, error, and success treatments as applicable. State text and focus indicators MUST satisfy the canonical contrast contract and MUST NOT rely on color alone.

#### Scenario: Segmented filter is selected
- **WHEN** a user changes a segmented filter in candidate results or admin reports
- **THEN** the selected option is exposed through accessible state and a governed selected treatment, not only through color

#### Scenario: Custom dropdown is used
- **WHEN** a custom dropdown is used instead of a native select
- **THEN** it provides label association, keyboard operation, focus management, and selected-state semantics

#### Scenario: OTP or profile validation state is shown
- **WHEN** login, registration, or profile validation fails or an action is pending
- **THEN** the affected control has an accessible name and invalid or busy state
- **AND** error or success feedback is announced through shared semantics without relying on color alone

#### Scenario: Single-choice question options are used
- **WHEN** a keyboard user enters a single-choice question option group
- **THEN** the group exposes native-equivalent radio semantics, one managed tab stop, and arrow-key movement between options
- **AND** Space or Enter selects the focused option without changing answer-save semantics

#### Scenario: Visible file picker is activated
- **WHEN** a keyboard user reaches an import or learning-video file-selection control
- **THEN** the visible trigger is focusable, has a visible focus indicator, and activates the native file selection behavior
- **AND** the selected filename and upload availability are communicated without bypassing existing validation

#### Scenario: Guarded exit warning opens
- **WHEN** leaving an active attempt requires a warning
- **THEN** the warning exposes its title and description, moves focus to the safe initial action, traps or manages focus for its modal behavior, and defines Escape behavior
- **AND** dismissing it returns focus to the action that opened it

#### Scenario: Shared control changes interaction state
- **WHEN** a shared action, field, select, file picker, or filter enters a disabled, pending, error, or success state
- **THEN** its visible label, focus behavior, accessible state, and contrast remain consistent with the canonical control contract
- **AND** a disabled or pending mutation cannot be mistaken for an available action

#### Scenario: Status color communicates meaning
- **WHEN** a control or feedback component uses color to distinguish a state
- **THEN** the same state is identifiable through text, iconography, shape, or accessible semantics
- **AND** the treatment meets the documented contrast target on its current surface

#### Scenario: Dialog or sheet content exceeds the viewport
- **WHEN** overlay content is taller than the available dynamic viewport, including mobile landscape or browser zoom
- **THEN** the overlay provides an internal scroll region and keeps its close control and required actions keyboard-reachable
- **AND** focus management continues to operate while the content scrolls

### Requirement: Responsive Design Consistency
The system SHALL keep Candidate Calm, Admin Workbench, Auth Canvas, and Exam Focus workflows usable without overlap or horizontal page overflow at 320, 375, 414, 430, and 768 CSS pixels, at representative desktop widths, in 844x390 and 896x414 mobile landscape, and at 200 percent browser zoom. The system SHALL preserve dynamic-viewport, safe-area, long-content, and reduced-motion behavior.

#### Scenario: Candidate focus mode is used on mobile
- **WHEN** the formal exam or practice focus page is viewed on a narrow or dynamic mobile viewport
- **THEN** fixed or sticky controls do not cover answer controls, question actions, feedback text, submit, or the device safe area
- **AND** answer-save controls and save status remain available with the same semantics as desktop

#### Scenario: Admin report actions wrap on mobile
- **WHEN** admin report filters, segmented controls, and export actions render on a narrow mobile viewport
- **THEN** the controls reflow according to the shared report-action contract without horizontal overflow
- **AND** the actionable label remains readable on one line within each reflowed control

#### Scenario: Registration and invitation pages are used on mobile
- **WHEN** a user completes registration, edits a profile, or opens an invited exam on a narrow viewport
- **THEN** fields, notices, invitation actions, and the next required action remain reachable and readable
- **AND** no fixed control or responsive data region introduces horizontal scrolling or obscures the task

#### Scenario: Mobile navigation content exceeds the available height
- **WHEN** candidate or admin navigation opens in mobile landscape or at 200 percent zoom
- **THEN** every navigation destination and logout action remains reachable through a dynamic-viewport-aware scroll region
- **AND** the overlay does not depend on a fixed `100vh` assumption

#### Scenario: Representative ordinary page is resized
- **WHEN** a representative list, form, dashboard, workspace, report, auth, or result page is viewed at a required viewport or populated with long Chinese text and unbroken identifiers
- **THEN** headings wrap safely, actions reflow, data regions use their documented compact presentation, and content remains within the viewport
- **AND** no root overflow rule hides an oversized interactive or content box

#### Scenario: Compact action text would wrap internally
- **WHEN** a navigation item, button, segmented option, or compact action does not fit its current row
- **THEN** the parent layout reflows the whole control while the actionable label remains on one line

#### Scenario: Exam workspace is resized or zoomed
- **WHEN** the exam-taking page is used at a required narrow viewport, in mobile landscape, or at 200 percent browser zoom
- **THEN** the active question, long option content, save state, navigation, and submit action remain reachable without horizontal overflow
- **AND** reduced-motion preferences continue to suppress nonessential motion

### Requirement: Admin Brand Mark Consistency
The system SHALL use a consistent brand glyph for the browser tab identity and repeated admin chrome wordmarks while preserving readable light and dark variants.

#### Scenario: Admin chrome renders brand identity
- **WHEN** an authenticated administrator views the desktop side rail or mobile admin header
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

### Requirement: Product Copy and Terminology Consistency
The system SHALL use Chinese-first, task-oriented product language across public, candidate, and admin pages. English SHALL appear only for the product name or a stable product or operational term whose presence adds meaning; ordinary pages MUST NOT require decorative bilingual eyebrows, routine all-caps English metadata, or faux chapter labels. General learning and practice surfaces SHALL refer to the authenticated person as `用户`, while formal exam roster and authorization surfaces SHALL use `应考人员`; those terms MUST NOT be mixed as interchangeable labels. Copy changes MUST preserve existing business meaning and MUST NOT expose raw API codes.

#### Scenario: Ordinary page or section label renders
- **WHEN** a public, candidate, or admin page renders a heading, section label, table label, or state label
- **THEN** Chinese text carries the primary task meaning
- **AND** decorative English is omitted unless the label uses an explicitly governed product or operational term

#### Scenario: Bilingual page labels render
- **WHEN** a product name or allowlisted stable operational term renders with both English and Chinese text
- **THEN** both labels describe the same canonical concept and Chinese remains the primary task language
- **AND** the bilingual treatment is not generalized into a routine eyebrow, table label, or decorative chapter marker

#### Scenario: Candidate role terms render
- **WHEN** candidate-facing login, exam list, practice, exam start, exam taking, result, or review pages refer to the current user
- **THEN** learning and practice copy uses the canonical `用户` terminology
- **AND** formal roster or authorization copy uses `应考人员` without implying that every user is an exam participant

#### Scenario: Admin roster terms render
- **WHEN** admin pages refer to exam-scoped participant lists, participant records, roster imports, or roster-management actions
- **THEN** visible copy uses the same canonical Chinese roster and participant terminology on desktop and responsive presentations

#### Scenario: Raw API codes would be visible
- **WHEN** a frontend page or component renders exam status, availability status, attempt status, question type, question status, or report status received from an API
- **THEN** the UI maps it to canonical user-facing Chinese text
- **AND** it does not expose raw codes such as `draft`, `active`, `archived`, `single`, `multiple`, `judge`, `not_started`, `in_progress`, or `submitted` as ordinary visible copy

#### Scenario: Candidate critical actions render
- **WHEN** the candidate exam workflow renders answer persistence, exam submission, or navigation away from the active exam surface
- **THEN** labels and feedback consistently distinguish saving answers, submitting the exam, staying in the exam, and returning to the exam list

#### Scenario: Admin report and table headers render
- **WHEN** a field appears in an admin table, responsive data card, form, filter, report, or export action
- **THEN** each presentation uses the same canonical Chinese field or action name

#### Scenario: Page states render
- **WHEN** loading, empty, disabled, stale, pending, success, or error states render for the same product object or action on related pages
- **THEN** state copy uses the same canonical Chinese object and action names
- **AND** it avoids contradictory terms or decorative English for the same condition

#### Scenario: Copy contract changes
- **WHEN** reusable headings, terminology, state labels, critical actions, or supporting copy are rewritten
- **THEN** focused tests cover the shared copy contract and high-risk visible labels
- **AND** route behavior, form meaning, API parameters, and business outcomes remain unchanged

### Requirement: Unified Email Login and Registration Challenge
The candidate frontend SHALL expose one email-only OTP entry point labeled `邮箱登录` for existing accounts and first-time registration. It MUST NOT request or display `employee_no`, `phone_suffix`, or a roster name as a prerequisite for the OTP request. After successful OTP verification, an active existing account receives the candidate session; an unknown mailbox receives a short-lived registration-completion challenge and MUST complete the profile step before receiving a candidate session.

#### Scenario: Existing user requests an OTP
- **GIVEN** an active platform account exists for the normalized email
- **WHEN** the user opens `邮箱登录`, enters the email, and selects `发送验证码`
- **THEN** the page creates one email OTP challenge without asking for employee number, phone suffix, or roster identity
- **AND** the page presents the OTP verification step without exposing account-enumeration details

#### Scenario: New mailbox requests an OTP
- **GIVEN** no platform account exists for the normalized email
- **WHEN** the user requests an OTP from `邮箱登录`
- **THEN** the page presents the same challenge response and verification step as an existing user
- **AND** it does not issue a candidate session before registration completion

#### Scenario: Existing user verifies an OTP
- **GIVEN** an unexpired, unused OTP challenge belongs to an active account
- **WHEN** the user enters the correct OTP and selects `验证并继续`
- **THEN** the frontend stores the four-hour candidate session in session-scoped browser state
- **AND** it returns the user to the preserved destination or the default user home

#### Scenario: Inactive user verifies an OTP
- **GIVEN** a correct OTP proves control of an email whose completed account is inactive
- **WHEN** verification returns the stable account-unavailable outcome
- **THEN** the frontend shows an actionable account-unavailable notice without storing a candidate session or registration credential
- **AND** it directs the user to contact an administrator for reactivation

### Requirement: Registration Completion and Profile Editing
The frontend SHALL provide a separate first-registration completion step that requires a display name after email verification and SHALL provide an account-profile page where an active user may edit the display name. The email is read-only in the first phase; email changes, physical deletion, and password fields MUST NOT be presented.

#### Scenario: New user completes registration
- **GIVEN** an OTP was verified for a new mailbox and a registration-completion credential is available
- **WHEN** the user enters a display name and submits the completion form
- **THEN** the account becomes active and the frontend receives the four-hour candidate session
- **AND** the user is returned to the preserved invitation or general-user destination

#### Scenario: Invited pending user receives a roster-name suggestion
- **GIVEN** a pending invite has a roster name associated with the verified email
- **WHEN** the first-registration form offers that value as the display-name suggestion
- **THEN** the user must explicitly confirm or edit the display name before submission
- **AND** the chosen account display name remains separate from the frozen formal roster name

#### Scenario: Registration completion is missing a display name
- **WHEN** a new user submits the registration-completion form without a display name
- **THEN** the page keeps the user on the completion step
- **AND** it exposes a field-level accessible error without issuing a candidate session

#### Scenario: Active user edits the display name
- **GIVEN** an authenticated active user opens the account profile page
- **WHEN** the user changes the display name and saves
- **THEN** the page shows a shared success state and subsequent general-user surfaces use the new display name
- **AND** the read-only normalized email remains unchanged

### Requirement: Invitation Deep-Link Return Preservation
The frontend MUST preserve a same-origin invited-exam destination across email OTP request, verification, registration completion, and session restoration. An invitation URL carries only the target exam/location and MUST NOT be treated as a bearer credential or authorization grant.

#### Scenario: Unauthenticated user opens an invitation link
- **GIVEN** a same-origin invitation link targets a published exam
- **WHEN** an unauthenticated user opens it
- **THEN** the frontend routes to `邮箱登录` with a validated return target containing the exam identifier
- **AND** it does not call the exam start API or grant formal access before authentication and exam scope authorization

#### Scenario: Existing user follows an invitation through OTP login
- **GIVEN** an invitation return target is present on the login route
- **WHEN** an existing active user verifies the OTP
- **THEN** the frontend navigates to the same exam destination after session creation
- **AND** the target is not replaced by the generic exam-list route

#### Scenario: New user follows an invitation through registration
- **GIVEN** an invitation return target is present and the mailbox is new
- **WHEN** the user verifies the OTP and completes the display-name step
- **THEN** the frontend navigates to the same exam destination after the candidate session is issued
- **AND** the invitation target remains only a navigation hint until the backend confirms exam scope

#### Scenario: Return target is unsafe or malformed
- **WHEN** a login or registration URL contains an external, protocol-relative, or malformed return target
- **THEN** the frontend discards that target and navigates to the safe general-user home after authentication

### Requirement: Invitation-Aware Exam States
The candidate exam list and start pages SHALL distinguish invited roster state, opening-time state, unavailable state, loading state, empty state, and error state. A published invited exam SHALL be visible to its scoped user immediately with its opening time, while the start action remains disabled until the backend permits it.

#### Scenario: Invited exam is before its opening time
- **GIVEN** the authenticated user is scoped to a published exam whose `available_from` is in the future
- **WHEN** the user opens the exam list
- **THEN** the exam card shows that the user is an invited `应考人员` and displays the opening time
- **AND** the start action is disabled with user-facing timing copy rather than a raw status code

#### Scenario: Invited exam becomes startable
- **GIVEN** the authenticated user is scoped to a published exam at or after its opening time
- **WHEN** the exam list refreshes successfully
- **THEN** the exam card enables the existing start/resume action
- **AND** the page preserves the same invitation and roster terminology

#### Scenario: User has no invited exams
- **GIVEN** the authenticated user has no published exam scope
- **WHEN** the exam-list query succeeds
- **THEN** the page renders a distinct empty state explaining that formal exams are invitation-only
- **AND** learning, practice, and wrong-question review remain discoverable as general-user features

#### Scenario: Invitation or exam query fails
- **WHEN** the invitation-aware exam-list or exam-detail query fails
- **THEN** the page renders a retryable error state with the canonical exam/邀请 terminology
- **AND** it does not render a blank, not-started, or unauthorized state as if the query had succeeded

### Requirement: Confirmed Email Login and OTP Copy
The login and registration surfaces SHALL use the confirmed copy contract exactly. The page title MUST be `邮箱登录`; the description MUST be `输入邮箱获取验证码。首次登录时，验证邮箱并填写姓名即可创建账号。`; after requesting an OTP, the dynamic guidance MUST be `验证码已发送至 {脱敏邮箱}，{有效分钟数} 分钟内有效。请查看收件箱和垃圾邮件；倒计时结束后可重新发送。`; the permission note MUST be `登录后可进行学习、练习和错题复习；正式考试仅对受邀用户开放。`; and the primary buttons MUST be `发送验证码` and `验证并继续` in their respective steps. OTP failure copy SHALL retain the neutral existing semantic and MUST NOT reveal account existence.

#### Scenario: Login copy renders before an OTP request
- **WHEN** a user opens the unauthenticated login page
- **THEN** the page renders the exact title, description, permission note, and `发送验证码` label from the confirmed copy contract
- **AND** it does not render employee number, phone suffix, or roster-name fields

#### Scenario: OTP guidance renders after a request
- **WHEN** an OTP request succeeds for any normalized email
- **THEN** the page renders the confirmed dynamic guidance with a masked email and the configured validity duration
- **AND** the primary action is labeled `验证并继续`

#### Scenario: OTP verification fails
- **WHEN** the entered OTP is invalid, expired, consumed, or attempt-exhausted
- **THEN** the page shows a neutral retry instruction using the existing semantic (`验证码无效或已过期，请重新获取后再试。` or an equivalent localized copy)
- **AND** it does not disclose whether the mailbox belongs to an existing account or roster

### Requirement: Four-Hour Candidate Session Without Remember-Me
The frontend SHALL keep the candidate session boundary at four hours, store session credentials only in `sessionStorage` or equivalent tab/session-scoped state, and MUST NOT offer a “remember me” control or persist candidate tokens in localStorage, cookies, URLs, invitation links, or other durable browser storage.

#### Scenario: Candidate session remains within four hours
- **GIVEN** a candidate session token has not reached its four-hour expiry
- **WHEN** the user reloads a candidate page in the same browser session
- **THEN** the frontend restores the session from session-scoped state and can request candidate APIs

#### Scenario: Candidate session expires
- **GIVEN** the four-hour candidate token has expired or has been globally revoked
- **WHEN** the user opens a protected candidate route
- **THEN** the frontend clears the stale session and redirects to `邮箱登录`
- **AND** it preserves a validated invitation return target when one was present

#### Scenario: User inspects login controls
- **WHEN** an unauthenticated user views the login or registration form
- **THEN** no remember-me checkbox, persistent-token option, or bearer credential appears in the visible UI or URL

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

### Requirement: Canonical Design Token Source of Truth
The frontend SHALL maintain one canonical source model for governed visual values. Runtime color, typography, spacing, target size, radius, elevation, focus, motion, and z-index literals SHALL be defined in the CSS root token source; structural breakpoint literals SHALL be defined in one typed build-time map consumed by responsive build and JavaScript code. Tailwind aliases, the exported TypeScript design-token map, media-query consumers, and `frontend/DESIGN.md` MUST reference or verifiably mirror those owners. Shared consumers and ordinary pages MUST use semantic aliases for governed typography, tracking, page spacing, control spacing, target size, radius, elevation, and status contrast. Any arbitrary visual literal or data-derived exception MUST be documented in a narrow allowlist. The canonical typography contract SHALL use the existing offline-safe system font stacks with documented CJK fallbacks and MUST NOT require an external or bundled font asset.

#### Scenario: Component needs a visual value
- **WHEN** a changed shared component or ordinary page needs a color, type size, tracking, page spacing, control spacing, radius, shadow, focus, motion, or status value
- **THEN** it references the corresponding semantic contract
- **AND** it does not introduce an untracked raw visual literal, legacy HSL token, or parallel token owner

#### Scenario: Local exception is necessary
- **WHEN** a data-derived identity color, safe-area calculation, state selector, or other legitimate local value cannot use the ordinary semantic aliases
- **THEN** the exception is narrowly owned, documented, and covered by the visual-policy allowlist
- **AND** it is not reused as a general page, surface, typography, or status value

#### Scenario: Token representation drifts
- **WHEN** the canonical runtime tokens, typed breakpoint map, Tailwind aliases, exported TypeScript design-token map, media-query consumers, visual-policy allowlist, or design documentation disagree
- **THEN** an automated consistency check fails before the change can be considered complete

#### Scenario: Responsive code needs a structural breakpoint
- **WHEN** build-time responsive styling or JavaScript media-query code needs a supported viewport threshold
- **THEN** it consumes the canonical typed breakpoint map rather than declaring an independent width literal
- **AND** CSS custom properties are not treated as media-query conditions

#### Scenario: Status treatment renders on dark or light surfaces
- **WHEN** success, warning, error, selected, or focus text appears on a supported surface
- **THEN** its text and non-text indicators meet the documented contrast target for that surface
- **AND** a state-specific on-dark or on-light token is used where the ordinary status token is insufficient

#### Scenario: External font services are unavailable
- **WHEN** the frontend runs in its supported offline or internal-network environment
- **THEN** the documented system font stacks render readable Latin and CJK text without a network or bundled font dependency

### Requirement: Typography and Editorial Hierarchy
The frontend SHALL use a redesigned but canonical system-font hierarchy with one page-level H1, ordered H2/H3 descendants, upright task labels, readable Chinese body text, and family-specific density. Editorial identity SHALL be expressed through scale, weight, whitespace, rules, and controlled asymmetry rather than repeated decorative English, faux chapter numbering, or italic headings.

#### Scenario: Ordinary page has no meaningful context label
- **WHEN** an ordinary page title fully identifies the current task
- **THEN** it renders the Chinese H1 without a forced eyebrow, translated duplicate, or faux chapter label

#### Scenario: Page context label adds real meaning
- **WHEN** a page needs a route family, workflow position, or operational state above its title
- **THEN** it renders at most one upright contextual label stacked with the title
- **AND** the label does not repeat the H1 or create a detached decorative heading column

#### Scenario: Page family applies typography density
- **WHEN** text hierarchy renders in Candidate Calm, Admin Workbench, Exam Focus, or Auth Canvas
- **THEN** it uses the documented scale and spacing for that family while retaining the same semantic heading and body roles
- **AND** pages do not invent local type sizes or tracking to simulate a new role

#### Scenario: Heading needs emphasis
- **WHEN** an H1, H2, or H3 needs visual emphasis
- **THEN** it uses scale, weight, ink contrast, whitespace, or a restrained rule while preserving normal font style

#### Scenario: Question position is shown
- **WHEN** Exam Focus communicates a genuine question position or sequence
- **THEN** ordinal text may use the documented compact or monospaced treatment
- **AND** that treatment is not generalized into decorative numbering on unrelated pages

### Requirement: Surface Hierarchy and Container Discipline
The frontend SHALL use a restrained canvas, plain section, panel, focus object, summary, and data-surface hierarchy. Each task region MUST have at most one primary containment owner for border, radius, background, padding, and elevation. Internal structure SHALL prefer whitespace, typography, and dividers; elevation SHALL be reserved for overlays and explicitly documented critical or summary emphasis.

#### Scenario: Metric grid is grouped
- **WHEN** metrics, fields, statuses, or records belong to one task region
- **THEN** either the outer region owns containment and its children remain visually subordinate, or individual children own containment inside a plain region
- **AND** the same group does not render card borders, radii, shadows, and padding at both levels

#### Scenario: Form or table surface renders
- **WHEN** a form, table, responsive data presentation, status group, report toolbar, or explanatory section renders
- **THEN** one documented surface or plain-section contract owns its boundary and spacing
- **AND** local wrappers do not introduce another decorative card layer

#### Scenario: Async state replaces content
- **WHEN** loading, empty, error, or stale feedback appears within an established region
- **THEN** it inherits the region's containment instead of adding an unrelated nested card

#### Scenario: Overlay or critical summary needs elevation
- **WHEN** a dialog, sheet, popover, or explicitly documented critical summary must separate from its canvas
- **THEN** it uses the governed elevation and surface treatment for that role
- **AND** ordinary page sections do not copy the same elevated treatment for decoration

### Requirement: Admin Navigation Information Architecture
The admin shell SHALL preserve every current navigation destination, route target, authorization boundary, and operational grouping while redesigning the navigation presentation for clearer hierarchy and compact workbench use. Desktop and mobile navigation MUST expose the same order, labels, active destination, and reachable logout action. Exam-specific context MUST continue to link only to existing authorized destinations.

#### Scenario: Administrator opens a primary admin destination
- **WHEN** an administrator opens dashboard, account, question, import, exam, learning, report, or operations content
- **THEN** the redesigned navigation exposes that existing destination within its canonical group and indicates the active item and group
- **AND** it does not add, remove, merge, or retarget a destination

#### Scenario: Administrator opens an exam-scoped destination
- **WHEN** an administrator opens an existing exam workspace, editor, roster or invitation, or result or review destination
- **THEN** the page identifies the current exam and related existing destinations without duplicating the page H1
- **AND** navigation does not bypass readiness, permission, or mutation guards

#### Scenario: Administrator uses mobile navigation
- **WHEN** the admin navigation opens on a narrow or short viewport
- **THEN** it preserves the desktop order, labels, active context, and logout action inside a reachable scroll region
- **AND** it introduces neither horizontal overflow nor inaccessible clipped destinations

#### Scenario: Administrator scrolls a long desktop page
- **WHEN** page content exceeds the desktop viewport height
- **THEN** the navigation remains viewport-stable and logout remains reachable without page-content height controlling its position

### Requirement: Admin Exam Workspace Visual Hierarchy
The admin exam workspace SHALL present one page title, exam lifecycle status and server observation time, one advisory next-action treatment, readiness and blockers, aggregate operational summaries, and deep links in that order of attention. It MUST preserve the aggregate, privacy, freshness, polling, and advisory semantics defined by the `admin-exam-workspace` capability.

#### Scenario: Workspace data is loading or unavailable
- **WHEN** no usable workspace aggregate is available
- **THEN** loading and recoverable error states use the shared page-state treatment
- **AND** the page does not invent default counts, readiness, or actions

#### Scenario: Workspace refresh fails with last good data
- **WHEN** a refresh fails after a usable aggregate was rendered
- **THEN** the last good aggregate and observation time remain visible with a stale notice and retry action
- **AND** the page does not replace the aggregate with an empty workspace

#### Scenario: Workspace recommends a next action
- **WHEN** the workspace aggregate returns an advisory next action
- **THEN** the page presents exactly one primary next-action treatment before supporting summaries
- **AND** the treatment does not grant permission or bypass the target page's existing mutation guard

#### Scenario: Workspace summaries render
- **WHEN** readiness, blocker, roster, invitation, attempt, incident, or result summaries render
- **THEN** they expose only the aggregates permitted by the workspace capability and no roster personally identifiable information
- **AND** related deep links use existing destinations

### Requirement: Exam Focus Visual Contract
The active exam interface SHALL use a dedicated, task-only composition that keeps the current question, semantically grouped options, timer, answer-save state and recovery, navigator, progress, guarded exit, and submit action reachable on desktop and mobile. It MUST NOT render unrelated ordinary candidate navigation while an attempt is active. Visual and accessibility changes MUST NOT alter start, save, submit, deadline, scoring, snapshot, retake, or auto-submit semantics defined by `exam-delivery`.

#### Scenario: Active exam renders on desktop
- **WHEN** an in-progress attempt renders at a desktop width
- **THEN** the question remains the primary content and the navigator remains an adjacent, scan-friendly secondary region
- **AND** timer, save state, progress, guarded exit, and submit remain reachable without ordinary-page chrome competing for attention

#### Scenario: Active exam renders on mobile
- **WHEN** an in-progress attempt renders at a narrow or short viewport
- **THEN** progress and navigation remain available through a dynamic-viewport-aware control and reachable overlay
- **AND** safe-area spacing prevents controls from covering the question, feedback, or submit action

#### Scenario: Exam Focus controls provide touch targets
- **WHEN** option, navigation, guarded-exit, save, or submit actions render in an Exam Focus touch layout
- **THEN** each action exposes a hit area of at least 44 by 44 CSS pixels without overlapping another action
- **AND** target sizing does not hide labels, answer content, persistence state, or safe-area spacing

#### Scenario: Candidate answers a single-choice question
- **WHEN** the active question accepts one option
- **THEN** its options expose radio-group semantics and expected keyboard navigation while preserving the existing answer value and save request

#### Scenario: Candidate requests to leave
- **WHEN** the candidate activates the attempt exit action
- **THEN** a semantically complete guarded warning explains the consequence, places focus on the safe action, and restores focus when dismissed
- **AND** confirmed navigation still uses the existing destination and unsaved-work rules

#### Scenario: Answer persistence state changes
- **WHEN** an answer is pending, saving, saved, offline, conflicted, or failed
- **THEN** visible state and recovery use canonical Chinese status language and accessible feedback
- **AND** the interface does not announce a saved state until persistence is confirmed

#### Scenario: Attempt reaches submission state
- **WHEN** a user submits or the delivery system auto-submits an attempt
- **THEN** the interface distinguishes pending, failed, submitted, and auto-submitted outcomes through text and accessible state
- **AND** submit cannot be confused with ordinary answer saving

### Requirement: Motion and Reduced-Motion Consistency
The frontend SHALL use named duration and easing tokens for permitted motion. Motion MUST support comprehension or state change, MUST be limited to transform and opacity where practical, and MUST provide a non-animated or minimal-opacity alternative when reduced motion is requested.

#### Scenario: Page-entry motion is used
- **WHEN** a page family opts into entry motion
- **THEN** it uses the documented short duration and easing tokens
- **AND** repeated workbench rows or cards do not receive decorative automatic staggering

#### Scenario: Loading shimmer or critical pulse would animate
- **WHEN** a user requests reduced motion
- **THEN** shimmer, pulse, zoom, and nonessential translation stop or become a brief opacity change
- **AND** loading or critical status remains understandable through static text and color-independent cues

#### Scenario: Modal or sheet opens
- **WHEN** a dialog or mobile navigation sheet transitions into view
- **THEN** its motion uses the canonical tokens and preserves focus management
- **AND** reduced-motion mode does not delay access to its controls

### Requirement: Rendered Visual Acceptance Evidence
A presentation-system change SHALL NOT be considered complete from static source inspection alone. The representative Auth Canvas, Candidate Calm, Admin Workbench, and Exam Focus routes MUST pass before broad migration, and every current route MUST subsequently have an applicable automated contract check or rendered browser observation for its family, relevant states, and viewport conditions. Evidence MUST be summarized in `docs/handoff.md`, and the implemented contract MUST remain synchronized with `frontend/DESIGN.md`.

#### Scenario: Representative route matrix is verified
- **WHEN** the first migration batch is evaluated
- **THEN** candidate login, exam list, active exam, result, admin dashboard, question form, and representative report surfaces are rendered at required mobile, tablet, desktop, zoom, and reduced-motion conditions
- **AND** broad route migration does not begin until the shared hierarchy, containment, actions, focus, and overflow checks pass

#### Scenario: Full current route inventory is verified
- **WHEN** the remaining presentation migration is complete
- **THEN** every current frontend route is mapped to a page family and has applicable ready, loading, empty, error, pending, success, long-content, or other relevant state evidence
- **AND** evidence confirms heading order, action reachability, visible focus, containment, readable Chinese copy, and absence of covered controls or horizontal overflow

#### Scenario: Browser exposes a visual or runtime regression
- **WHEN** a route has an unexpected console error, horizontal overflow, obscured action, missing focus indicator, unreadable state, broken hierarchy, or ungoverned decorative treatment
- **THEN** the change remains incomplete until the issue is corrected or a narrow documented exception is approved

#### Scenario: Specialized focus route is assessed
- **WHEN** Exam Focus is included in visual acceptance
- **THEN** it is evaluated against the dedicated Exam Focus contract rather than ordinary page-header or candidate-navigation expectations

#### Scenario: Disposable browser evidence is recorded
- **WHEN** local or containerized browser evidence passes
- **THEN** the handoff identifies the environment, browser, route states, and covered viewports
- **AND** it does not present that evidence as formal Mac or Windows acceptance unless the corresponding host workflow was actually run

### Requirement: Exam Result Information Hierarchy
The candidate result experience SHALL present outcome, score or pass summary, available attempt context, breakdown or filtering, and question review in a stable task order. Available attempt context MUST be derived only from current route or query state and fields already returned by existing result queries. The presentation MAY be recomposed, but it MUST preserve the current result data, filter behavior, answer correctness, snapshot-based review, and navigation semantics without requiring a new endpoint or response field. Result hierarchy MUST use one primary summary treatment and MUST NOT create competing nested summary cards for the same outcome.

#### Scenario: Candidate opens a completed result
- **WHEN** a submitted attempt result is available
- **THEN** the page first communicates the outcome and primary score or pass information, then supporting attempt context and review controls
- **AND** the same data and correctness semantics remain available after the visual recomposition

#### Scenario: Result context is limited to existing data
- **WHEN** the redesigned result summary needs attempt context
- **THEN** it uses only the existing route parameters, selected attempt identifier, and result fields already available to the page
- **AND** it does not add or require an API request, endpoint, or response field

#### Scenario: Candidate filters or reviews result questions
- **WHEN** the candidate changes a result filter or opens question review content
- **THEN** the active filter, question order, saved answer, correct answer, analysis, and awarded score remain consistent with the existing result behavior
- **AND** the review region remains visually subordinate to the primary result summary without nested-card duplication

#### Scenario: Result is viewed on a narrow viewport
- **WHEN** the result summary and review render at a supported mobile width or 200 percent zoom
- **THEN** outcome, score, filters, and review actions remain readable and reachable without horizontal overflow or covered content

### Requirement: Presentation-System Drift Governance
The frontend SHALL enforce the canonical presentation contract through automated source policy, a documented exception allowlist, route-family coverage, and observed rendered evidence. A passing build alone MUST NOT establish visual completion.

#### Scenario: Source introduces a governed visual bypass
- **WHEN** changed production source introduces a raw color, undeclared font asset, arbitrary typography or tracking value, independent page-width owner, duplicated surface treatment, or unsupported responsive breakpoint
- **THEN** an automated policy check fails unless the usage is a documented narrow exception

#### Scenario: Representative pattern is approved for broad migration
- **WHEN** a shared page, surface, field, status, action, report, data, or navigation pattern passes its representative route checks
- **THEN** remaining routes reuse that approved contract rather than creating page-specific visual variants

#### Scenario: Canonical documentation or evidence drifts
- **WHEN** implementation changes a governed presentation rule or verification result
- **THEN** `frontend/DESIGN.md` and the relevant automated checks are updated with the implementation
- **AND** `docs/handoff.md` records only commands and browser evidence actually observed
