# Frontend Page Experience Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
