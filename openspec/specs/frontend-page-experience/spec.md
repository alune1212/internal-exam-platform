# Frontend Page Experience Specification

## Purpose

Frontend page experience covers required query states, design-system composition, accessibility semantics, and responsive behavior across candidate and admin pages.
## Requirements
### Requirement: Frontend Page Query States
The system SHALL distinguish required frontend query loading, empty, and error states on candidate and admin pages, including the invitation target and registration/profile queries. A page MUST NOT turn a pending or failed invitation/account query into an empty exam list or a form with default data.

#### Scenario: Required page query is loading
- **WHEN** a page waits for required query data before it can render meaningful content
- **THEN** the page renders an Academic Editorial loading state using the shared page or table-state primitives

#### Scenario: Required page query fails
- **WHEN** a required candidate or admin page query fails before usable data is available
- **THEN** the page renders an error state instead of showing an empty list, default form data, or an indefinite loading state

#### Scenario: Required page query succeeds with no rows
- **WHEN** a required list or table query succeeds and returns no rows
- **THEN** the page renders an empty state that is visually distinct from loading and error states

#### Scenario: Invitation target query is pending or unavailable
- **WHEN** a login, registration, or exam-list page is resolving an invitation target
- **THEN** the page keeps the return target and renders a loading or error state as appropriate
- **AND** it does not claim that the user has no invitation merely because the query has not completed

### Requirement: Data-Dependent Admin Actions
The system MUST NOT expose admin mutation actions that depend on unresolved required query data.

#### Scenario: Administrator opens an exam edit page before the exam record loads
- **WHEN** the exam edit page has not loaded the target exam record
- **THEN** the page does not present editable default exam values or a save action for those defaults

#### Scenario: Administrator opens an exam candidate page before exam state loads
- **WHEN** the exam candidate page has not resolved whether the exam is frozen
- **THEN** the page does not present import, remove, or retake actions as if the exam state were known

### Requirement: Design-System Page Composition
The system SHALL compose ordinary candidate and admin pages, including email login, registration completion, account profile, and invitation-aware exam pages, from the shared frontend design primitives defined by `frontend/DESIGN.md`.

#### Scenario: Ordinary page renders its main heading
- **WHEN** an ordinary candidate or admin page renders
- **THEN** it uses a single page-level H1 through `PageHeader` or an equivalent heading that follows the documented H1 class contract

#### Scenario: Specialized exam workflow renders
- **WHEN** the formal exam-taking or practice focus workflow renders its active question interface
- **THEN** it may use specialized question, timer, option, and navigator components while preserving shared token, radius, focus, and state conventions

#### Scenario: Local forms and feedback render
- **WHEN** frontend pages render repeated form fields, textareas, alerts, status pills, or feedback notices
- **THEN** they prefer existing local UI, page, and editorial primitives before introducing hand-written styling

#### Scenario: Login, registration, and profile pages render
- **WHEN** an email login, first-registration profile, or account-profile page renders
- **THEN** its fields, actions, notices, and validation feedback use the shared `Field`, `Input`, `Button`, `Alert`, `Card`, `PageHeader`, and `PageSection` primitives or their documented equivalents

### Requirement: Accessible Stateful Controls
The system SHALL expose semantic state and keyboard/focus behavior for custom or segmented frontend controls, including OTP verification, registration completion, profile editing, and invitation actions.

#### Scenario: Segmented filter is selected
- **WHEN** a user changes a segmented filter in candidate results or admin reports
- **THEN** the selected option is exposed through accessible state, not only through visual color

#### Scenario: Custom dropdown is used
- **WHEN** a custom dropdown is used instead of a native select
- **THEN** it provides label association, keyboard operation, focus management, and selected-state semantics

#### Scenario: OTP or profile validation state is shown
- **WHEN** login, registration, or profile validation fails or an action is pending
- **THEN** the affected control has an accessible name and invalid/busy state
- **AND** the error or success feedback is announced through the shared alert/error semantics without relying on color alone

### Requirement: Responsive Design Consistency
The system SHALL keep mobile candidate and admin workflows usable without overlap or horizontal overflow, including email login, registration completion, account profile, and invitation-aware exam states.

#### Scenario: Candidate focus mode is used on mobile
- **WHEN** the formal exam or practice focus page is viewed on a narrow mobile viewport
- **THEN** fixed bottom navigation does not cover answer controls, question actions, or feedback text

#### Scenario: Admin report actions wrap on mobile
- **WHEN** admin report filters, segmented controls, and export actions render on a narrow mobile viewport
- **THEN** the controls wrap within the page header without horizontal overflow

#### Scenario: Registration and invitation pages are used on mobile
- **WHEN** a user completes registration, edits a profile, or opens an invited exam on a narrow viewport
- **THEN** fields, OTP controls, notices, and invitation actions remain reachable and readable
- **AND** no fixed action or responsive table obscures the next required action or introduces horizontal scrolling

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
The system SHALL use synchronized Chinese-English product terminology for visible frontend copy across public, candidate, and admin pages. General learning/practice surfaces SHALL refer to the authenticated person as a user (`用户`), while formal exam roster and exam authorization surfaces SHALL use the participant term (`应考人员`); the two terms MUST NOT be mixed as interchangeable labels.

#### Scenario: Bilingual page labels render
- **WHEN** a public, candidate, or admin page renders a bilingual eyebrow, section label, compact heading, or table label
- **THEN** the English and Chinese text describe the same canonical product concept from the shared copy contract

#### Scenario: Candidate role terms render
- **WHEN** candidate-facing login, exam list, practice, exam start, exam taking, result, or review pages refer to the current user
- **THEN** learning and practice copy uses the canonical user terminology
- **AND** formal roster/authorization copy uses `应考人员` and does not imply that every user is an exam participant

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
