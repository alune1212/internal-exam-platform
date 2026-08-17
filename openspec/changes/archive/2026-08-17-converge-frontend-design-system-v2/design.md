# Design: Frontend Presentation-System Convergence V2

## Context

See `proposal.md` for motivation. The archived `unify-frontend-visual-system` change established the current canonical foundation: warm-paper and ink tokens, offline-safe system fonts, four page families, shared primitives, grouped admin navigation, motion rules, and a deterministic visual route matrix. This change starts from that implemented baseline; it does not replace it with another theme or component library.

The remaining problem is consumer convergence. Current source and rendered-route review found several classes of drift:

- candidate and admin layouts constrain content width before `PageShell`, while individual pages add further width overrides;
- decorative bilingual context labels and arbitrary tracking remain common even though contextual labels are supposed to be optional;
- page sections, cards, forms, statuses, report actions, and responsive data views still have multiple local visual owners;
- active formal exam content remains under ordinary candidate navigation, and some custom exam/file/overlay controls do not yet provide native-equivalent keyboard and focus behavior;
- the visual suite establishes a strong technical baseline, but it does not yet open every high-risk control state or require route-wide convergence after representative pages pass.

The active Windows and macOS portability changes also modify `frontend-page-experience`. This design must preserve their browser-support, offline-asset, and formal-host boundaries. It must also preserve the current authentication/session boundary, API clients, route paths, navigation destinations, exam snapshots, answer persistence, scoring, submission, retake, invitation, import, and report behavior.

## Goals / Non-Goals

**Goals:**

- Keep the current palette and restrained Academic Editorial tone while rebuilding navigation presentation, typography hierarchy, page frames, ordinary page skeletons, and result composition.
- Make shared patterns, rather than pages, own width, containment, fields, statuses, actions, report controls, and responsive data presentation.
- Make Chinese the primary task language and rewrite visible copy directly without changing business meaning.
- Preserve intentional density differences between Candidate Calm, Admin Workbench, Exam Focus, and Auth Canvas.
- Correct high-risk keyboard, focus, contrast, dynamic-viewport, and long-content gaps as part of the same presentation contract.
- Migrate through representative routes first and enforce route-wide rendered and source-policy evidence before completion.

**Non-Goals:**

- No new color theme, font asset, component framework, route path, navigation destination, API, persistence model, or backend behavior.
- No workflow or information-architecture rewrite beyond visual hierarchy and copy inside existing routes and existing navigation groups.
- No change to authorization, session storage, exam lifecycle, answer release, snapshot-based review, saving, submit, scoring, retake, import, or report filtering.
- No broad cleanup outside the presentation consumers touched by the migration.
- No substitution of disposable Chromium checks for formal host or browser acceptance.

## Decisions

### 1. Treat V2 as consumer convergence, not a second token rewrite

The existing ownership model remains:

- CSS root variables own literal runtime visual values;
- the typed breakpoint map owns structural viewport thresholds;
- Tailwind exposes semantic aliases;
- shared primitives consume those aliases;
- `frontend/DESIGN.md` documents the contract and exceptions.

V2 may add missing semantic roles such as page-frame widths, action alignment, control-state contrast, type roles, tracking roles, a 44 CSS-pixel Exam Focus touch-target minimum, and overlay viewport behavior. It will not rename the palette wholesale or introduce a parallel token registry. Existing system-font stacks remain canonical; the redesigned hierarchy changes scale, weight, line height, wrapping, and spacing rather than font files.

Changed shared consumers and ordinary pages must use semantic typography and layout roles. Legitimate arbitrary selectors, safe-area calculations, grid calculations, and the owned data-derived avatar palette remain documented exceptions. A source-policy test will distinguish those exceptions from page-level visual improvisation rather than banning every bracketed Tailwind expression.

The button success treatment must use a contrast-safe on-dark or alternate-surface token. Status alpha borders must use values that the build can generate deterministically instead of relying on an unsupported opacity composition.

**Alternatives considered**

- Replace the existing tokens and rebuild the component library: rejected because color ownership and shared-control adoption are already strong.
- Add a Chinese webfont or bundled font family: rejected because the user selected the existing system stack and the platform must remain offline-safe.
- Ban all arbitrary Tailwind values: rejected because accessibility selectors, data states, safe areas, and computed layout values have legitimate uses.

### 2. Give page framing one owner

Layout responsibilities will be separated:

| Layer | Owns | Does not own |
| --- | --- | --- |
| Application/session boundary | authentication checks, browser support, outlet context | page width or page-specific density |
| Family layout | canvas and family chrome | content max-width variants selected by a page |
| Page frame | horizontal page padding, content width, block rhythm, family density | local surface styling |
| Page composition | semantic sections and task order | new global width, radius, shadow, or typography contracts |

`PageShell` or its compatible successor becomes the sole ordinary-page frame. Its width roles will describe intent—reading, standard, wide, and full/focus—rather than competing `max-w-*` values. Candidate and admin layouts stop imposing a second content max-width. Pages choose one documented role and cannot override it with another page-level maximum except through a narrow documented exception.

Auth Canvas and active Exam Focus remain specialized frames. They use the same tokens and responsive rules but do not inherit ordinary-page chrome or an ordinary-page H1 requirement.

**Alternatives considered**

- Keep layout and page max-widths and only normalize their values: rejected because a nominal wide page would still be constrained by an outer owner.
- Let every route choose arbitrary maximum widths: rejected because it is the current source of cross-page rhythm drift.

### 3. Rebuild editorial hierarchy around Chinese task language

The current shared copy boundary remains the source for reusable visible text, but its contract changes from routine bilingual labels to Chinese-first task language:

- Chinese headings, labels, actions, and statuses carry the primary meaning;
- English is allowlisted for the product name or a stable operational term only;
- decorative all-caps translations, faux chapter labels, and duplicated bilingual table metadata are removed;
- one ordinary page has one H1 and at most one meaningful context label;
- `用户` and `应考人员` retain their established distinct meanings;
- raw enums remain mapped to user-facing Chinese copy;
- saving answers, submitting an exam, staying in an attempt, and leaving an attempt remain unambiguous.

The implementation may rewrite all current UI copy without a separate per-string approval gate. It may not invent new product concepts, change a field's meaning, merge actions, change report dimensions, or alter route/return behavior. A canonical glossary and focused copy tests protect those boundaries.

Typography expresses editorial identity through system-font scale, weight, whitespace, rules, and controlled asymmetry. H1/H2/H3, navigation, actions, statuses, metrics, question labels, and table labels remain upright. Question positions and operational identifiers may use the governed monospaced role.

**Alternatives considered**

- Preserve bilingual labels and only standardize their tracking: rejected because their frequency is itself the hierarchy problem.
- Rewrite product flows together with the copy: rejected by the locked route and business boundary.

### 4. Preserve four families with explicit density and chrome contracts

| Family | Current route intent | Chrome | Density and attention |
| --- | --- | --- | --- |
| Auth Canvas | candidate login/registration and admin login | no candidate/admin shell | minimal; identity step, recovery, one primary action |
| Candidate Calm | learning, practice entry/review, exam list/start/result, profile | current candidate destinations in redesigned presentation | calm; one current task and restrained supporting context |
| Admin Workbench | dashboard, accounts, questions/import, exams/workspace, learning, reports, operations | current grouped destinations in redesigned presentation | compact; scan status, data, filters, and operations |
| Exam Focus | active formal exam and active practice question | dedicated task-only chrome | focused; question, timer, persistence, navigator, progress, guarded exit, submit |

The family contract is shared grammar, not identical markup. Candidate cards need not match admin data surfaces, and Exam Focus does not receive ordinary navigation simply for global consistency.

The current candidate layout combines session enforcement and ordinary navigation. Implementation will separate presentation mode from session behavior without changing paths:

- the formal taking route declares the focus family statically;
- active practice can request the focus family while its question workspace is mounted and restore Candidate Calm when the workspace exits;
- auth routes continue to render without application chrome;
- candidate session and safe-return behavior remain in the existing protected boundary.

This must be implemented as an explicit shell contract, not by visually covering ordinary navigation with a fixed-position layer.

**Alternatives considered**

- Keep ordinary candidate navigation visible during attempts: rejected because it competes with the timed task and contradicts the focus contract.
- Change the practice or exam route paths to encode the shell: rejected because paths and return behavior are compatibility boundaries.
- Hide chrome with an overlay: rejected because duplicate focusable navigation would remain in the accessibility tree.

### 5. Consolidate repeated presentation patterns around existing primitives

The implementation will extend or compose the current local primitives rather than add a second UI layer:

| Pattern | Contract |
| --- | --- |
| Page frame | one width, page padding, density, and vertical-rhythm owner |
| Surface | plain, panel, focus/summary, data, and overlay roles; one containment owner per task group |
| Form field | label, description, error, disabled, pending, and success association |
| Status family | page state, actionable alert, inline pill, and timeline dot have distinct responsibilities |
| Action group | authentication, page, form-footer, card, and toolbar actions use documented alignment and mobile reflow |
| Report toolbar | filters, segments, notices, and export share one responsive order |
| Responsive data | desktop table and mobile card representation share labels, density, actions, and overflow rules |

Existing `PageSection`, `Card`, `Field`, `StatusPill`, `PageState`, report, and data-table components may be evolved or composed to satisfy these roles. New component names are not a goal. The deciding rule is ownership: the same task group cannot receive independent background, border, radius, shadow, and padding from both parent and child.

One primary surface per task region does not mean every responsive table card is forbidden. A mobile row card is a documented representation of the data surface, not an additional nested page surface. Overlays and the primary result summary may use governed elevation; ordinary page sections prefer canvas, whitespace, dividers, and typographic hierarchy.

### 6. Redesign navigation presentation without changing navigation information architecture

Candidate and admin navigation may change shape, spacing, type hierarchy, active treatment, responsive arrangement, and brand presentation. They must preserve the existing destinations, route targets, authorization, and canonical order.

Admin desktop and mobile navigation continue to derive from one model and expose the same operational groups. Exam context navigation continues to point only to existing workspace, edit, roster/invitation, and filtered result/review destinations. No redesign may create a route, grant a permission, move a mutation into navigation, or bypass readiness gates.

Mobile sheets must use the available dynamic viewport, provide internal scrolling, retain safe-area padding, and keep logout and every destination keyboard-reachable. Desktop navigation remains viewport-stable on long pages.

### 7. Recompose the result page without changing result truth

The result page will use a stable attention order:

1. submitted outcome and primary score/pass summary;
2. attempt identity and supporting context;
3. result filters or breakdown controls when available;
4. snapshot-based question review.

The composition has one primary summary treatment. Supporting metrics and review rows cannot compete through repeated dark cards or nested elevated surfaces. The redesign may change the current asymmetric grid, summary colors within the retained palette, and responsive arrangement.

It must preserve the attempt selected by the current query state, score and pass calculation, question order, saved answer, correct answer, analysis, awarded score, filters, and answer-release gating. Attempt context may use only the existing route parameters, selected attempt identifier, and fields already returned by the current result queries; it cannot require a new endpoint or response field. If answers or analysis are not released, the redesigned page must not reveal them merely to fill a visual region.

### 8. Fold interaction accessibility into the shared visual contract

High-risk controls will use native semantics or native-equivalent behavior:

- single-choice exam options use a labelled radio group with roving focus or native inputs and arrow-key navigation;
- multiple-choice options retain checkbox semantics;
- guarded attempt exit uses a real modal-dialog contract with description association, safe initial focus, Escape behavior, focus containment, and focus restoration;
- visible file-selection triggers are keyboard-focusable and activate the native input;
- dialogs and sheets provide dynamic-viewport max height and internal scrolling;
- mutations consume the shared pending/busy state rather than only changing text and disabling locally;
- ordinary buttons receive a governed pressed state without layout movement;
- Exam Focus option, navigation, guarded-exit, save, and submit actions expose a hit area of at least 44 by 44 CSS pixels on touch layouts;
- success, warning, error, selection, and focus contrast are verified on each supported surface.

These changes affect interaction mechanics only enough to satisfy established semantics. They do not change answer values, save timing, mutation requests, or validation rules.

### 9. Use representative-first migration and route-wide completion gates

The first migration batch is fixed:

- candidate login;
- candidate exam list;
- active formal exam;
- candidate result;
- admin dashboard;
- question create/edit form state;
- one representative admin report.

This batch exercises Auth Canvas, Candidate Calm, Exam Focus, and Admin Workbench plus form, status, surface, data, navigation, and action contracts. Shared contracts must pass focused tests and rendered checks before remaining pages migrate.

After the representative gate, every current route is assigned to a family and a migration inventory. Each route receives the states relevant to it rather than artificial universal states. The route inventory must explicitly include the question create/edit dialog, learning-video file selection and dialog, long candidate identifiers, result answer-release states, mobile navigation overflow, active exam exit, and long option content.

The browser matrix remains 320x844, 375x812, 414x896, 430x932, 768x1024, 1280x900, 844x390, and 896x414, with 200-percent zoom and reduced-motion spot checks. Assertions include:

- layout overflow measured with root clipping disabled;
- visible interactive bounds and uncovered required actions;
- at least 44-by-44 CSS-pixel touch hit areas for Exam Focus option, navigation, guarded-exit, save, and submit actions;
- heading order and family chrome;
- one-line compact labels with parent reflow;
- focus-visible, selected, invalid, busy, dialog, and radio behavior;
- dynamic-viewport overlay reachability and safe-area controls;
- long Chinese and unbroken-identifier stress content;
- expected page states and no unexpected console errors.

Generated screenshots remain test artifacts. `docs/handoff.md` records exact commands, environment, routes, viewports, failures, skips, and the separation from formal host acceptance.

### 10. Make drift policy precise enough to keep legitimate exceptions

A focused source-policy test will scan production frontend consumers for:

- raw colors outside canonical owners and documented data-derived exceptions;
- external or bundled font introductions;
- arbitrary typography and tracking outside the allowlist;
- independent page-width and breakpoint literals;
- duplicated complete surface treatments in ordinary pages;
- unsupported motion values and legacy token families;
- automatic workbench staggering;
- copy patterns that reintroduce routine decorative bilingual labels.

The policy will not mechanically reject state selectors, ARIA/data variants, safe-area calculations, responsive grid calculations, or documented media/deep-chrome exceptions. Exceptions must identify their owner and reason. Updating an exception is a contract change, not a silent lint suppression.

## Risks / Trade-offs

- **[The change overlaps active Windows/macOS `frontend-page-experience` deltas]** → Preserve their normative requirements, validate all OpenSpec changes together, and keep host-specific evidence separate from the visual migration.
- **[Large visual diffs become hard to review]** → Land foundations, shared patterns, representative routes, and remaining families as atomic gates; do not mix backend or business changes into those diffs.
- **[Chinese copy rewrite changes product meaning]** → Maintain a tested canonical glossary, preserve field/action mapping, and keep route/API/form behavior tests as compatibility gates.
- **[System-font metrics vary across operating systems]** → Avoid fixed-height text containers, test CJK and long identifiers, and accept controlled line-wrap variation rather than pixel identity.
- **[Flattening surfaces removes useful grouping]** → Remove duplicate containment only; keep headings, rules, whitespace, semantic groups, and documented responsive data-row boundaries.
- **[Suppressing ordinary chrome breaks session or return behavior]** → Separate presentation mode from the session boundary, retain a guarded exit, and regression-test login return, logout, exam-list return, and unauthorized handling.
- **[Accessibility mechanics alter exam input behavior]** → Preserve answer values and request boundaries, add focused keyboard tests, and run the existing exam-delivery component/browser gates.
- **[All-route browser coverage becomes slow or brittle]** → Keep deterministic route-state fixtures, run a small representative gate first, then shard the route matrix while retaining one canonical inventory.
- **[Source policy rejects legitimate Tailwind syntax]** → Start from an audited allowlist and require ownership/reason metadata instead of applying a blanket arbitrary-value ban.
- **[Disposable screenshots are mistaken for release acceptance]** → Label them as engineering evidence and leave formal host commissioning to the existing portability changes.

## Migration Plan

1. **Baseline and compatibility guards** — record the current route inventory, copy inventory, arbitrary-value inventory, rendered baseline, and focused route/API/exam behavior tests; reconcile this delta with active Windows/macOS OpenSpec requirements.
2. **Contract and policy** — update `frontend/DESIGN.md` to V2, define the glossary and English allowlist, add semantic type/layout/state roles, and introduce source-policy tests before consumer migration.
3. **Frame and shared patterns** — establish single page-width ownership, family presentation modes, restrained surfaces, unified fields/statuses/actions/report/data contracts, and overlay/control accessibility.
4. **Representative routes** — migrate the fixed seven-route/state batch and pass the focused unit/component and rendered acceptance gate.
5. **Remaining route inventory** — migrate remaining Candidate Calm, Admin Workbench, Auth Canvas, and active Practice focus states using approved patterns; resolve every source-policy exception deliberately.
6. **Full verification and evidence** — run formatting, unit/component, lint, build, offline, visual matrix, formal-exam disposable browser gate, OpenSpec strict validation, and diff checks; update `docs/handoff.md` only with observed evidence.

Each phase must keep the frontend buildable and behavior tests green. No phase may mark later route or browser evidence complete based on planned results.

### Rollback

- Contract/token and shared-pattern changes remain separate from route migrations and can be reverted independently.
- Representative and remaining pages can roll back family by family because routes, APIs, and stored data do not change.
- The candidate focus-shell presentation can revert without changing attempt state or session storage.
- No database migration, endpoint removal, route rename, asset dependency, or deployment ordering change requires data recovery.

## Open Questions

None. The user resolved the high-impact choices before proposal creation: keep the palette and Academic Editorial tone, redesign presentation structure, retain routes/business/API/system fonts, use Chinese-first direct copy rewrite, preserve four family densities, migrate representative routes first, and require strict route-wide acceptance.
