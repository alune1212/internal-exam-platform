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
The system SHALL compose frontend pages from the canonical design contract defined by `frontend/DESIGN.md`. Ordinary pages MUST use shared tokens and primitives while preserving four explicit composition contexts: Candidate Calm, Admin Workbench, Exam Focus, and the chrome-free Auth Canvas. These composition rules MUST NOT change route authorization, API contracts, or exam-delivery semantics.

#### Scenario: Ordinary page renders its main heading
- **WHEN** an ordinary candidate or admin page renders
- **THEN** it uses a single page-level H1 through `PageHeader` or an equivalent heading that follows the documented H1 contract
- **AND** any context label is optional, meaningful, upright, and visually subordinate to the H1

#### Scenario: Ordinary candidate page renders
- **WHEN** a candidate opens an ordinary learning, practice-entry, exam-list, result, review, or profile page
- **THEN** the page uses Candidate Calm composition with the candidate top navigation and calm page density
- **AND** it does not render the admin side rail or the active-attempt navigator

#### Scenario: Ordinary admin page renders
- **WHEN** an administrator opens a dashboard, list, import, edit, workspace, operations, or report page
- **THEN** the page uses Admin Workbench composition with the admin navigation and scan-friendly page density
- **AND** it does not use a marketing hero or candidate navigation

#### Scenario: Specialized exam workflow renders
- **WHEN** the formal exam-taking or practice focus workflow renders its active question interface
- **THEN** it uses Exam Focus composition and may use specialized question, timer, option, and navigator components
- **AND** it preserves shared token, radius, focus, state, and typography conventions without forcing the ordinary `PageHeader`

#### Scenario: Authentication canvas renders
- **WHEN** a login, registration, or registration-completion route renders before the application shell is available
- **THEN** it omits candidate top navigation, admin side navigation, and a decorative global footer
- **AND** its fields, actions, notices, and validation feedback still use the shared form and feedback primitives

#### Scenario: Local forms and feedback render
- **WHEN** frontend pages render repeated form fields, textareas, selects, alerts, status pills, or feedback notices
- **THEN** they prefer existing local UI, page, and editorial primitives before introducing hand-written styling

#### Scenario: Login, registration, and profile pages render
- **WHEN** an email login, first-registration profile, or account-profile page renders
- **THEN** its fields, actions, notices, and validation feedback use the shared `Field`, `Input`, `Button`, `Alert`, `Card`, `PageHeader`, and `PageSection` primitives or their documented equivalents

### Requirement: Accessible Stateful Controls
The system SHALL expose semantic state and keyboard/focus behavior for native, custom, and segmented frontend controls, including OTP verification, registration completion, profile editing, invitation actions, filters, imports, and shared select controls. Repeated controls SHALL provide documented default, hover, focus-visible, active, disabled, loading, error, and success treatments as applicable.

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

#### Scenario: Shared control changes interaction state
- **WHEN** a shared button, field, select, file picker, or filter enters a disabled, loading, error, or success state
- **THEN** its visible label, focus behavior, and accessible state remain consistent with the canonical control contract
- **AND** a disabled or pending mutation cannot be mistaken for an available action

#### Scenario: Status color communicates meaning
- **WHEN** a control or feedback component uses color to distinguish a state
- **THEN** the same state is also identifiable through text, iconography, shape, or accessible semantics

### Requirement: Responsive Design Consistency
The system SHALL keep Candidate Calm, Admin Workbench, Auth Canvas, and Exam Focus workflows usable without overlap or horizontal page overflow at 320, 375, 414, 430, and 768 CSS pixels, at representative desktop widths, in mobile landscape, and at 200 percent browser zoom. The system SHALL preserve safe-area support and reduced-motion behavior.

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
- **WHEN** the exam-taking page is used at 320, 375, 414, or 430 CSS pixels, in mobile landscape, or at 200 percent browser zoom
- **THEN** the active question, options, save state, navigation, and submit action remain reachable without horizontal overflow
- **AND** reduced-motion preferences continue to suppress nonessential motion

#### Scenario: Representative ordinary page is resized
- **WHEN** a representative candidate or admin list, form, workspace, or report is viewed at 320, 375, 414, or 768 CSS pixels or at 200 percent browser zoom
- **THEN** page headings wrap safely, action groups reflow, responsive tables use their documented compact presentation, and the page does not scroll horizontally

#### Scenario: Compact action text would wrap internally
- **WHEN** a navigation item, button, segmented option, or compact action does not fit its current row
- **THEN** the parent layout reflows the whole control while the actionable label remains on one line

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
The frontend SHALL maintain one canonical source model for governed visual values. Runtime color, typography, spacing, radius, elevation, focus, motion, and z-index literals SHALL be defined in the CSS root token source; structural breakpoint literals SHALL be defined in one typed build-time map consumed by Tailwind and JavaScript media-query code. TypeScript visual-token access, component styles, and `frontend/DESIGN.md` MUST reference or verifiably mirror those owners. The canonical typography contract SHALL use the existing offline-safe system font stacks with documented CJK fallbacks and MUST NOT require an undeclared external font request.

#### Scenario: Component needs a visual value
- **WHEN** a changed component needs a color, font family, spacing, radius, shadow, focus, or motion value
- **THEN** it references a named canonical token or an explicitly documented data-derived exception
- **AND** it does not introduce an untracked raw visual literal or legacy HSL design token

#### Scenario: Token representation drifts
- **WHEN** the canonical runtime tokens, typed breakpoint map, Tailwind aliases, TypeScript visual-token references, media-query consumers, or design documentation disagree about a governed value
- **THEN** an automated consistency check fails before the change can be considered complete

#### Scenario: Responsive code needs a structural breakpoint
- **WHEN** Tailwind or JavaScript media-query code needs a supported viewport threshold
- **THEN** it consumes the typed build-time breakpoint map rather than declaring an independent width literal
- **AND** CSS custom properties are not treated as media-query conditions

#### Scenario: External font services are unavailable
- **WHEN** the frontend runs in its supported offline or internal-network environment
- **THEN** the documented system font stacks render readable Latin and CJK text without a network font dependency

### Requirement: Typography and Editorial Hierarchy
The frontend SHALL use one page-level H1, ordered H2/H3 descendants, upright heading styles, and optional contextual labels. Decorative English metadata, faux chapter numbering, and italic headings MUST NOT be required to identify ordinary pages. English metadata MAY appear when it communicates a real product concept and remains synchronized with the canonical Chinese terminology.

#### Scenario: Ordinary page has no meaningful context label
- **WHEN** an ordinary page title fully identifies the current task
- **THEN** the page renders the H1 without a forced eyebrow or faux chapter label

#### Scenario: Page context label adds real meaning
- **WHEN** a page needs a route family, workflow position, or operational status above its title
- **THEN** it renders at most one upright contextual label stacked with the title
- **AND** the label does not compete with or sit as a detached left-hand heading column

#### Scenario: Heading needs emphasis
- **WHEN** an H1, H2, or H3 needs visual emphasis
- **THEN** it uses weight, color, size, or a restrained rule while preserving normal font style

#### Scenario: Question position is shown
- **WHEN** Exam Focus communicates a genuine question position or sequence
- **THEN** ordinal text may use the documented compact or monospaced treatment
- **AND** it is not generalized into decorative chapter numbering on unrelated pages

### Requirement: Surface Hierarchy and Container Discipline
The frontend SHALL use the documented canvas, plain section, panel, focus card, and table surface hierarchy. A visual group MUST have one owner for border, radius, background, and elevation; parent and child containers MUST NOT both present independent card treatment for the same group.

#### Scenario: Metric grid is grouped
- **WHEN** metric cards appear inside a page section
- **THEN** either the outer section is visually plain and the metric cards own containment, or the outer surface owns containment and the metric children are borderless
- **AND** both levels do not independently render card borders and shadows

#### Scenario: Form or table surface renders
- **WHEN** a form, table, status group, or explanatory section renders
- **THEN** one documented surface variant owns its boundary and spacing
- **AND** inner layout wrappers do not add another decorative card layer

#### Scenario: Async state replaces content
- **WHEN** loading, empty, error, or stale feedback appears within an established section
- **THEN** it inherits the existing section containment instead of adding an unrelated nested card

### Requirement: Admin Navigation Information Architecture
The admin shell SHALL group existing destinations into stable operational domains and SHALL expose the current group and destination on desktop and mobile. Exam-specific destinations SHALL provide an accessible exam context without changing routes, permissions, mutation guards, or the underlying navigation targets. Logout MUST remain reachable within the viewport.

#### Scenario: Administrator opens a primary admin destination
- **WHEN** an administrator opens dashboard, account, question, import, exam, learning, report, or operations content
- **THEN** the navigation exposes the destination within its canonical group and indicates the active item and group

#### Scenario: Administrator opens an exam-scoped destination
- **WHEN** an administrator opens an existing exam workspace, editor, roster/invitation, or result/review destination, including monitoring content presented inside the workspace
- **THEN** the shell or page-level context identifies the current exam and related destinations
- **AND** links lead to existing authorized pages without bypassing readiness or mutation guards

#### Scenario: Administrator uses mobile navigation
- **WHEN** the admin navigation sheet opens on a narrow viewport
- **THEN** it preserves the same group order, labels, active context, and reachable logout action as the desktop navigation
- **AND** it introduces no horizontal overflow

#### Scenario: Administrator scrolls a long desktop page
- **WHEN** page content exceeds the desktop viewport height
- **THEN** the side rail remains viewport-stable and logout remains near the visible rail bottom

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
The active exam interface SHALL preserve a specialized focus composition that keeps the current question, options, timer, answer-save state and recovery, navigator, progress, and submit action reachable and semantically exposed on desktop and mobile. Visual-system changes MUST NOT alter start, save, submit, deadline, scoring, snapshot, retake, or auto-submit semantics defined by `exam-delivery`.

#### Scenario: Active exam renders on desktop
- **WHEN** an in-progress attempt renders at a desktop width
- **THEN** the question remains the primary content and the navigator remains an adjacent, scan-friendly secondary region
- **AND** timer, save state, progress, and submit remain reachable without ordinary-page chrome competing for attention

#### Scenario: Active exam renders on mobile
- **WHEN** an in-progress attempt renders at a narrow viewport
- **THEN** progress and navigation remain available through the documented bottom control and sheet pattern
- **AND** safe-area spacing prevents those controls from covering the question, feedback, or submit action

#### Scenario: Answer persistence state changes
- **WHEN** an answer is pending, saving, saved, offline, conflicted, or failed
- **THEN** the visible state and recovery action use the canonical status language and semantic feedback
- **AND** the interface does not announce a saved state until persistence is confirmed

#### Scenario: Attempt reaches submission state
- **WHEN** a user submits or the delivery system auto-submits an attempt
- **THEN** the interface distinguishes pending, failed, submitted, and auto-submitted outcomes through text and accessible state
- **AND** the submit action cannot be confused with ordinary answer saving

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
A visual-system change SHALL NOT be considered complete from static source inspection alone. Representative Candidate Calm, Admin Workbench, Auth Canvas, and Exam Focus routes MUST have automated checks and rendered browser evidence for their relevant states and viewport matrix. The evidence MUST be summarized in `docs/handoff.md`, and the implemented contract MUST remain synchronized with `frontend/DESIGN.md`.

#### Scenario: Representative route matrix is verified
- **WHEN** implementation verification runs
- **THEN** representative list, form, workspace, report, auth, active-exam, and result surfaces are rendered at their required mobile, tablet, desktop, zoom, and reduced-motion conditions
- **AND** evidence confirms page family, heading hierarchy, surface containment, action reachability, visible focus, and absence of horizontal overflow or covered controls

#### Scenario: Browser exposes a visual or runtime regression
- **WHEN** a representative route has an unexpected console error, horizontal overflow, obscured action, missing focus indicator, unreadable state, or broken hierarchy
- **THEN** the visual-system change remains incomplete until the issue is corrected or an explicit scoped exception is documented

#### Scenario: Specialized focus route is assessed
- **WHEN** Exam Focus is included in visual acceptance
- **THEN** it is evaluated against the Exam Focus contract rather than ordinary `PageHeader`, admin navigation, or footer expectations

#### Scenario: Disposable browser evidence is recorded
- **WHEN** local or containerized browser evidence passes
- **THEN** the handoff identifies the environment and covered viewports
- **AND** it does not present that evidence as formal Mac or Windows acceptance unless the corresponding host workflow was actually run
